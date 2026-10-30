# ruff: noqa: E501 - Browser expressions are kept together.
"""Issue #305 source-tree HTTP/browser evidence in disposable synthetic homes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests'), str(ROOT)]

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_language_switch_context import switch  # noqa: E402
from test_manual_review_play_navigation import (  # noqa: E402
    BACK,
    OPTIONS,
    PLAY,
    RESET,
    UNDO,
    append,
    play_page,
    setup_pages,
)
from test_manual_review_saved_names import snapshot  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402
from verify_recording_deletion import click, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.guided_rendering as rendering  # noqa: E402
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.app_web.profile_driven_creation as creation  # noqa: E402
import skatmind.app_web.workflow_operations as operations  # noqa: E402
from skatmind.app_web.historical_form import build_historical_play_view_v1  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402


def form(route):
    return f'form[action="{route}"]'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('before', 'after'), required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    assert Path(rendering.__file__).resolve().is_relative_to(ROOT / 'src')
    local = LocalBrowser(args.browser, args.output / 'browser-profile')
    cdp = local.cdp
    report = {'completed': False, 'phase': args.phase, 'python': sys.version,
              'browser': local.version, 'measurements': [], 'cases': [],
              'source': rendering.__file__, 'resources': {},
              'zoom_boundary': 'Actual 100% browser zoom; CSS viewport emulation is not enlarged browser zoom. Installed enlarged-zoom acceptance remains pending.'}
    for name in ('guided_rendering.py', 'compact_card_rendering.py', 'assets/app.css',
                 'assets/workflow.js', 'locales/de.json', 'locales/en.json'):
        report['resources'][name] = hashlib.sha256((Path(rendering.__file__).parent / name).read_bytes()).hexdigest()

    def measure(case, directory, stage, widths=(1365, 520, 320)):
        for width in widths:
            cdp.call('Emulation.setDeviceMetricsOverride', width=width, height=900, deviceScaleFactor=1, mobile=False)
            time.sleep(.1)
            data = cdp.evaluate('''(()=>{let f=document.querySelector('.wizard-actions'),b=f.querySelector('form[action="/actions/review/back"] button'),r=f.querySelector('.reset-form'),p=document.querySelector('#field-card');const rect=e=>{if(!e)return null;let x=e.getBoundingClientRect();return {x:x.x,y:x.y,width:x.width,height:x.height}};return {locale:document.documentElement.lang,viewport:innerWidth,document:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,dpr:devicePixelRatio,scale:visualViewport.scale,footer:rect(f),back:rect(b),backForm:rect(b?.form),reset:rect(r),resetMargin:getComputedStyle(r).marginTop,consent:rect(r.querySelector('label')),selects:document.querySelectorAll('select[name=card]').length,radios:document.querySelectorAll('input[type=radio][name=card]').length,groups:p?[...p.querySelectorAll('.compact-card-group')].map(g=>{let rows=new Map();for(let l of g.querySelectorAll('label')){let y=l.getBoundingClientRect().y;rows.set(y,(rows.get(y)||0)+1)}return {width:g.getBoundingClientRect().width,rows:[...rows.values()]}}):[],tiles:p?[...p.querySelectorAll('label')].map(l=>({height:l.getBoundingClientRect().height,font:getComputedStyle(l).fontSize,input:l.querySelector('input').getBoundingClientRect().width,overflow:l.scrollWidth>l.clientWidth+1,name:l.querySelector('input').getAttribute('aria-label')})):[]}})()''')
            data.update(case=case['name'], stage=stage, zoom=cdp.call('Page.getLayoutMetrics')['cssVisualViewport'].get('zoom'))
            report['measurements'].append(data)
            assert data['zoom'] == data['dpr'] == data['scale'] == 1
            if args.phase == 'before':
                assert data['selects'] == 1 and data['radios'] == 0
                if width == 1365:
                    assert data['back']['height'] > 100, data
            else:
                assert data['document'] == data['client'], data
                assert data['resetMargin'] == '0px', data
                if data['back']:
                    assert data['back']['height'] == data['backForm']['height'] == 44, data
                    assert data['reset']['height'] > data['back']['height'], data
                else:
                    assert stage == 'step-1'
                for tile in data['tiles']:
                    assert tile['height'] >= 44 and tile['font'] == '16px' and tile['input'] == 20
                    assert not tile['overflow'] and tile['name']
                for group in data['groups']:
                    if sum(group['rows']) == 8:
                        assert group['rows'] in ([8], [4, 4], [2]*4, [1]*8)
                        if width >= 1365:
                            assert group['rows'] == [8]
            cdp.evaluate('document.querySelector(".wizard-actions").scrollIntoView({block:"center"})')
            cdp.screenshot(directory / f'{stage}-footer-{width}.png')
            if data['radios']:
                cdp.evaluate('document.querySelector("#field-card").scrollIntoView({block:"start"})')
                cdp.screenshot(directory / f'{stage}-cards-{width}.png')

    def submit(case, selector, *, native_keyboard=False):
        count = len(case['posts'])
        if native_keyboard:
            tab_to(cdp, selector)
            keyboard(cdp, 'Enter', 'Enter', 13, '\r')
        else:
            click(cdp, selector)
        for _ in range(100):
            if len(case['posts']) > count:
                break
            time.sleep(.1)
        else:
            raise AssertionError(('No POST response', selector))
        time.sleep(.4)
        return case['posts'][-1]

    def checked():
        return cdp.evaluate('[...document.querySelectorAll("input[name=card]:checked")].map(e=>e.value)')

    def offered():
        return cdp.evaluate('[...document.querySelectorAll("input[name=card]")].map(e=>e.value)')

    def initial(directory, stage, server):
        cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
        cdp.navigate(server.origin + '/review')
        cdp.screenshot(directory / f'{stage}-initial.png')

    try:
        for locale in ('de', 'en'):
            for script in (False, True):
                name = f'{locale}-{script}'
                directory = args.output / name
                directory.mkdir()
                fixture = localized_server.__wrapped__(directory)
                server = next(fixture)
                case = {'name': name, 'javascript': script, 'locale': locale, 'posts': [],
                        'phase': 'fixture', 'phases': {}}
                report['cases'].append(case)
                counts = Counter()
                real_replace, real_response = os.replace, Handler.send_response

                def counted(name, real, counts=counts):
                    def call(*a, **kw):
                        counts[name] += 1
                        return real(*a, **kw)
                    return call

                def replaced(source, destination, server=server, counts=counts, real=real_replace):
                    if Path(destination).is_relative_to(server.app_context.managed_home.root):
                        counts['persistent_replacements'] += 1
                    return real(source, destination)

                def responded(handler, status, *a, case=case, real=real_response, **kw):
                    if handler.command == 'POST':
                        case['posts'].append({'phase': case['phase'], 'path': handler.path, 'status': status})
                    return real(handler, status, *a, **kw)

                def checkpoint(next_phase, case=case, counts=counts):
                    if case['phase'].startswith('passive-'):
                        assert not counts
                        assert not any(p['phase'] == case['phase'] for p in case['posts'])
                    case['phases'].setdefault(case['phase'], []).append(dict(counts))
                    counts.clear()
                    case['phase'] = next_phase

                try:
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(os, 'replace', replaced))
                        stack.enter_context(patch.object(Handler, 'send_response', responded))
                        for module, attr, label in (
                            (profile, 'save_frontend_profile_file_v1', 'profile_saves'),
                            (operations, 'execute_guided_frontend_analysis_v1', 'analysis'),
                            (operations, 'execute_guided_frontend_review_v1', 'review'),
                            (learning, 'prepare_learning_corpus_artifacts_web_v1', 'learning_preparation'),
                            (creation, 'generate_frontend_match_id_v1', 'match_ids'),
                            (creation, 'generate_frontend_player_id_v1', 'player_ids'),
                            (creation, 'generate_frontend_session_id_v1', 'session_ids'),
                            (creation, 'generate_frontend_corpus_id_v1', 'corpus_ids'),
                        ):
                            stack.enter_context(patch.object(module, attr, counted(label, getattr(module, attr))))
                        http = Browser(server)
                        switch(http, http.page('/review'), locale)
                        cdp.call('Network.setCookie', name=http.cookie.split('=', 1)[0], value=http.cookie.split('=', 1)[1], url=server.origin, httpOnly=True, sameSite='Strict')
                        cdp.call('Emulation.setScriptExecutionDisabled', value=not script)
                        for route, resource in (('/assets/app.css', 'assets/app.css'),
                                                ('/matches/assets/capture.js', 'assets/workflow.js')):
                            status, _, raw = http.request('GET', route)
                            assert status == 200 and hashlib.sha256(raw).hexdigest() == report['resources'][resource]
                        pages = [play_page(http)] if args.phase == 'before' else setup_pages(http)
                        for step, page in enumerate(pages, 1):
                            stage = 'step-5' if args.phase == 'before' else f'step-{step}'
                            (directory / f'{stage}.html').write_text(page, encoding='utf-8')
                            checkpoint('passive-' + stage)
                            before = snapshot(server.app_context)
                            initial(directory, stage, server)
                            measure(case, directory, stage)
                            assert snapshot(server.app_context) == before
                            checkpoint('fixture')
                        if args.phase == 'before':
                            checkpoint('complete')
                            continue
                        checkpoint('passive-selection')
                        initial(directory, 'play-interaction', server)
                        measure(case, directory, 'wide-play', widths=(1920, 2560, 440))
                        cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
                        state = server.app_context.review_state
                        assert checked() == []
                        # Native required selection blocks the ordinary button without a POST.
                        click(cdp, form(PLAY) + ' button')
                        assert server.app_context.review_state is state
                        assert cdp.evaluate('document.activeElement.name') == 'card'
                        # Bypass only browser constraint checking to inspect a genuine server rejection.
                        checkpoint('missing-rejection')
                        cdp.evaluate('document.querySelector(' + json.dumps(form(PLAY)) + ').noValidate=true')
                        assert submit(case, form(PLAY) + ' button')['status'] == 400
                        case['initial_error_focus'] = cdp.evaluate('({tag:document.activeElement.tagName,cls:document.activeElement.className})')
                        assert case['initial_error_focus'] == {'tag': 'SECTION', 'cls': 'error-summary'}
                        assert cdp.evaluate('document.querySelector(".field-error").parentElement.id') == 'field-card'
                        cdp.screenshot(directory / 'rejection-initial.png')
                        click(cdp, '.error-summary a')
                        assert cdp.evaluate('document.activeElement.id') == 'field-card'
                        assert server.app_context.review_state is state
                        checkpoint('language-empty')
                        other = 'en' if locale == 'de' else 'de'
                        submit(case, f'.language-selector button[value="{other}"]')
                        assert checked() == []
                        checkpoint('passive-keyboard')
                        before = snapshot(server.app_context)
                        # Natural group entry, Space selection, Arrow change, then Tab exits the group.
                        tab_to(cdp, 'input[name=card]')
                        keyboard(cdp, ' ', 'Space', 32, ' ')
                        assert checked() == ['CA']
                        keyboard(cdp, 'ArrowRight', 'ArrowRight', 39)
                        assert checked() == ['C10']
                        case['radio_focus'] = cdp.evaluate('(()=>{let e=document.activeElement,s=getComputedStyle(e.closest("label"));return {value:e.value,outline:s.outlineWidth,shadow:s.boxShadow}})()')
                        assert case['radio_focus']['outline'] == '3px'
                        cdp.screenshot(directory / 'radio-keyboard-focus.png')
                        keyboard(cdp, 'Tab', 'Tab', 9)
                        assert cdp.evaluate('document.activeElement.matches(' + json.dumps(form(PLAY) + ' button') + ')')
                        click(cdp, 'input[name=card][value=SA]')
                        time.sleep(.2)
                        network_count = len(cdp.events)
                        click(cdp, 'input[name=card][value=C10]')
                        keyboard(cdp, 'ArrowRight', 'ArrowRight', 39)
                        time.sleep(.2)
                        assert len(cdp.events) == network_count
                        click(cdp, 'input[name=card][value=SA]')
                        assert snapshot(server.app_context) == before and server.app_context.review_state is state
                        checkpoint('language-selected')
                        submit(case, f'.language-selector button[value="{locale}"]')
                        assert checked() == (['SA'] if script else [])
                        assert server.app_context.review_state is state
                        checkpoint('explicit-plays')
                        click(cdp, 'input[name=card][value=SA]')
                        submit(case, form(PLAY) + ' button', native_keyboard=True)
                        assert offered() == ['SK', 'SQ', 'S9', 'S8', 'S7'] and checked() == []
                        assert len(server.app_context.review_state.draft.plays) == 1
                        checkpoint('passive-restricted')
                        measure(case, directory, 'restricted')
                        checkpoint('explicit-plays')
                        click(cdp, 'input[name=card][value=SK]')
                        submit(case, form(PLAY) + ' button')
                        click(cdp, 'input[name=card][value=H9]')
                        submit(case, form(PLAY) + ' button')
                        view = build_historical_play_view_v1(server.app_context.review_state.draft)
                        assert view.last_trick_winner_player_id == view.acting_player_id == 'frontend-forehand'
                        assert len(view.completed_tricks) == 1 and not view.current_trick_plays
                        checkpoint('undo-back')
                        submit(case, form(UNDO) + ' button', native_keyboard=True)
                        state = server.app_context.review_state
                        count = len(case['posts'])
                        submit(case, form(BACK) + ' button', native_keyboard=True)
                        assert case['posts'][count:] == [{'phase': 'undo-back', 'path': BACK, 'status': 303}]
                        assert server.app_context.review_state.draft.plays == state.draft.plays
                        submit(case, 'form[action="/actions/review/update-discards"] button')
                        for _ in range(2):
                            submit(case, form(UNDO) + ' button')
                        checkpoint('explicit-singleton')
                        click(cdp, 'input[name=card][value=CJ]')
                        submit(case, form(PLAY) + ' button')
                        assert offered() == ['SJ'] and checked() == []
                        checkpoint('passive-singleton')
                        measure(case, directory, 'singleton')
                        tab_to(cdp, 'input[name=card]')
                        keyboard(cdp, ' ', 'Space', 32, ' ')
                        assert checked() == ['SJ']
                        checkpoint('explicit-singleton')
                        submit(case, form(PLAY) + ' button', native_keyboard=True)
                        checkpoint('supported-completion-fixture')
                        page = http.page('/review')
                        while len(server.app_context.review_state.draft.plays) < 30:
                            view = build_historical_play_view_v1(server.app_context.review_state.draft)
                            page = append(http, page, view.legal_cards[0])
                        checkpoint('passive-step-6')
                        initial(directory, 'step-6', server)
                        measure(case, directory, 'step-6')
                        checkpoint('complete-back-continue')
                        submit(case, form(BACK) + ' button', native_keyboard=True)
                        assert not offered() and not cdp.evaluate('!!document.querySelector("select[name=card]")')
                        assert len(server.app_context.review_state.draft.plays) == 30
                        cdp.screenshot(directory / 'complete-play-initial.png')
                        submit(case, form(PLAY) + ' button', native_keyboard=True)
                        assert server.app_context.review_state.draft.step == 6
                        submit(case, form(OPTIONS) + ' button')
                        checkpoint('passive-step-7-downloads')
                        initial(directory, 'step-7', server)
                        measure(case, directory, 'step-7')
                        before = snapshot(server.app_context)
                        state = server.app_context.review_state
                        # No execution was requested; unavailable downloads cannot manufacture Results.
                        for route in ('/downloads/review/request.json', '/downloads/review/result.json'):
                            assert http.request('GET', route)[0] == 404
                        click(cdp, form(RESET) + ' button')
                        assert server.app_context.review_state is state and snapshot(server.app_context) == before
                        checkpoint('reset-rejection')
                        cdp.evaluate('document.querySelector(' + json.dumps(form(RESET)) + ').noValidate=true')
                        assert submit(case, form(RESET) + ' button')['status'] == 400
                        assert server.app_context.review_state is state
                        assert not cdp.evaluate('document.querySelector("input[name=confirm_reset]").checked')
                        checkpoint('explicit-reset')
                        click(cdp, 'input[name=confirm_reset]')
                        assert submit(case, form(RESET) + ' button')['status'] == 303
                        assert server.app_context.review_state.draft is None
                        assert snapshot(server.app_context) == before
                        checkpoint('complete')
                finally:
                    try:
                        next(fixture)
                    except StopIteration:
                        pass
        report['completed'] = True
        report['operation_totals'] = dict(sum((Counter(values) for case in report['cases']
            for phases in case['phases'].values() for values in phases), Counter()))
        report['post_totals'] = dict(Counter(f"{p['status']} {p['path']}"
            for case in report['cases'] for p in case['posts']))
    finally:
        local.close()
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'completed': report['completed'], 'cases': len(report['cases']),
                      'measurements': len(report['measurements']),
                      'operations': report.get('operation_totals'),
                      'posts': report.get('post_totals'), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
