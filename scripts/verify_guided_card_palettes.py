# ruff: noqa: E501 - Browser expressions are kept together.
"""Issue #304 disposable source-tree browser evidence; never installed UAT data."""

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
from test_compact_card_entry_web import create_live  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_card_palettes import CARDS, DEAL, deal_page  # noqa: E402
from test_language_switch_context import switch  # noqa: E402
from test_manual_review_saved_names import snapshot  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402
from verify_recording_deletion import click, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.guided_rendering as rendering  # noqa: E402
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.app_web.profile_driven_creation as creation  # noqa: E402
import skatmind.app_web.workflow_operations as operations  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402


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
              'browser': local.version, 'cases': [], 'measurements': [],
              'source': rendering.__file__, 'resources': {},
              'zoom': 'Measured 100% browser zoom; emulated CSS viewport sizes are not zoom. Enlarged real zoom remains for installed acceptance.'}
    for name in ('guided_rendering.py', 'compact_card_rendering.py', 'assets/app.css',
                 'assets/workflow.js', 'locales/de.json', 'locales/en.json'):
        report['resources'][name] = hashlib.sha256((Path(rendering.__file__).parent / name).read_bytes()).hexdigest()

    def measure(case, stage, widths=(1365, 1920, 2560, 520, 440, 420, 320)):
        for width in widths:
            cdp.call('Emulation.setDeviceMetricsOverride', width=width, height=900, deviceScaleFactor=1, mobile=False)
            time.sleep(.1)
            data = cdp.evaluate("""(()=>{const palettes=[...document.querySelectorAll('.card-palette,.compact-cards')];return {width:innerWidth,document:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,dpr:devicePixelRatio,scale:visualViewport.scale,palettes:palettes.map(p=>({name:p.querySelector('input')?.name,width:p.getBoundingClientRect().width,groups:[...p.querySelectorAll('.compact-card-group,.card-grid')].map(g=>{let rows=new Map();for(const l of g.querySelectorAll('label')){let r=l.getBoundingClientRect(),y=Math.round(r.y*10)/10;if(!rows.has(y))rows.set(y,[]);rows.get(y).push(l.querySelector('input').value)}return {width:g.getBoundingClientRect().width,heading:g.querySelector('h4')?.textContent,rows:[...rows.values()]}}),tiles:[...p.querySelectorAll('label')].map(l=>{let r=l.getBoundingClientRect(),i=l.querySelector('input');return {height:r.height,width:r.width,font:getComputedStyle(l).fontSize,input:i.getBoundingClientRect().width,overflow:l.scrollWidth>l.clientWidth+1,name:i.getAttribute('aria-label')}})}))}})()""")
            data.update(case=case['name'], stage=stage,
                        locale=cdp.evaluate('document.documentElement.lang'),
                        zoom=cdp.call('Page.getLayoutMetrics')['cssVisualViewport'].get('zoom'))
            report['measurements'].append(data)
            assert data['zoom'] == 1 and data['dpr'] == data['scale'] == 1
            if args.phase == 'after':
                assert data['document'] == data['client'], data
                for palette in data['palettes']:
                    for tile in palette['tiles']:
                        assert tile['height'] >= 44 and tile['font'] == '16px' and tile['input'] == 20
                        assert not tile['overflow'] and tile['name']
                    for group in palette['groups']:
                        rows = group['rows']
                        if sum(map(len, rows)) == 8:
                            assert list(map(len, rows)) in ([8], [4, 4], [2]*4, [1]*8), group
                            if width >= 1365:
                                assert len(rows) == 1, group
            # Initial delivery is captured separately, before any scrolling/focus.
            if width in (1365, 320):
                for field in dict.fromkeys(p['name'] for p in data['palettes']):
                    selector = f'input[name="{field}"][type="checkbox"]'
                    if not cdp.evaluate('!!document.querySelector(' + json.dumps(selector) + ')'):
                        selector = f'input[name="{field}"][type="radio"]'
                    cdp.evaluate('document.querySelector(' + json.dumps(selector) + ').closest("fieldset").scrollIntoView({block:"start"})')
                    cdp.screenshot(args.output / f"{case['name']}-{stage}-{width}-{field}.png")

    def submit(selector, *, pointer=True):
        posts = report['cases'][-1]['posts']
        before = len(posts)
        if pointer:
            click(cdp, selector)
        else:
            tab_to(cdp, selector)
            keyboard(cdp, 'Enter', 'Enter', 13, '\r')
        for _ in range(1200):
            if len(posts) > before:
                break
            time.sleep(.1)
        else:
            raise AssertionError(('No POST response', selector, cdp.evaluate(
                '[...document.querySelectorAll(":invalid")].map(e=>({name:e.name,value:e.value}))')))
        time.sleep(.5)

    def checked(field):
        return cdp.evaluate('[...document.querySelectorAll(' + json.dumps(f'input[name="{field}"]:checked') + ')].map(e=>e.value)')

    def select(field, cards):
        for card in CARDS:
            selector = f'input[name="{field}"][value="{card}"]'
            exists = cdp.evaluate('!!document.querySelector(' + json.dumps(selector) + ')')
            if exists and ((card in checked(field)) != (card in cards)):
                click(cdp, selector)

    def keyboard_pair(field, first, second):
        click(cdp, f'input[name="{field}"][value="{first}"]')
        keyboard(cdp, 'Tab', 'Tab', 9)
        assert cdp.evaluate('({name:document.activeElement.name,value:document.activeElement.value})') == {
            'name': field, 'value': second}
        keyboard(cdp, ' ', 'Space', 32, ' ')
        assert checked(field) == [first, second]

    try:
        for locale in ('de', 'en'):
            for script in (False, True):
                case = {'name': f'{locale}-{script}', 'locale': locale, 'javascript': script, 'posts': [], 'phases': {}}
                report['cases'].append(case)
                directory = args.output / case['name']
                directory.mkdir()
                fixture = localized_server.__wrapped__(directory)
                server = next(fixture)
                counts = Counter()
                case['phase'] = 'fixture'
                real_replace = os.replace
                real_response = Handler.send_response

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
                        for module, name, label in (
                            (profile, 'save_frontend_profile_file_v1', 'profile_saves'),
                            (operations, 'execute_guided_frontend_analysis_v1', 'analysis'),
                            (operations, 'execute_guided_frontend_review_v1', 'review'),
                            (learning, 'prepare_learning_corpus_artifacts_web_v1', 'learning_preparation'),
                            (creation, 'generate_frontend_match_id_v1', 'match_ids'),
                            (creation, 'generate_frontend_player_id_v1', 'player_ids'),
                            (creation, 'generate_frontend_session_id_v1', 'session_ids'),
                            (creation, 'generate_frontend_corpus_id_v1', 'corpus_ids'),
                        ):
                            stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
                        http = Browser(server)
                        switch(http, deal_page(http), locale)
                        for route, name in (('/assets/app.css', 'assets/app.css'),
                                            ('/matches/assets/capture.js', 'assets/workflow.js')):
                            status, _, raw = http.request('GET', route)
                            assert status == 200 and hashlib.sha256(raw).hexdigest() == report['resources'][name]
                        cdp.call('Network.setCookie', name=http.cookie.split('=', 1)[0], value=http.cookie.split('=', 1)[1], url=server.origin, httpOnly=True, sameSite='Strict')
                        cdp.call('Emulation.setScriptExecutionDisabled', value=not script)
                        cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
                        checkpoint('passive-layout')
                        before = snapshot(server.app_context)
                        cdp.navigate(server.origin + '/review')
                        cdp.screenshot(args.output / f"{case['name']}-deal-initial.png")
                        measure(case, 'deal')
                        assert snapshot(server.app_context) == before and not counts
                        if args.phase == 'before':
                            checkpoint('complete')
                            continue
                        # Actual container transitions including one track, without shrinking text.
                        # A local verifier-only parent width probes the existing container query.
                        cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
                        case['container_probes'] = []
                        for width in (770, 767, 386, 383, 194, 191):
                            cdp.evaluate(f'document.querySelector(".card-palette .compact-card-groups").style.width="{width}px"')
                            tracks = cdp.evaluate('getComputedStyle(document.querySelector(".card-palette .compact-card-choices")).gridTemplateColumns.split(" ").length')
                            rows = cdp.evaluate('(()=>{let rows=new Map();for(const l of document.querySelector(".card-palette .compact-card-choices").children){let y=l.getBoundingClientRect().y;rows.set(y,(rows.get(y)||0)+1)}return [...rows.values()]})()')
                            case['container_probes'].append({'width': width, 'tracks': tracks, 'rows': rows})
                            assert tracks == (8 if width >= 768 else 4 if width >= 384 else 2 if width >= 192 else 1)
                            assert rows == [tracks] * (8 // tracks)
                            cdp.evaluate('document.querySelector(".card-palette .compact-card-groups").scrollIntoView({block:"start"})')
                            assert cdp.evaluate('[...document.querySelectorAll(".card-palette:first-of-type label")].every(e=>e.scrollWidth<=e.clientWidth+1)')
                            cdp.screenshot(args.output / f"{case['name']}-container-{width}.png")
                        cdp.evaluate('document.querySelector(".card-palette .compact-card-groups").style.removeProperty("width")')
                        cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
                        # Pointer followed by natural Tab/Space, no checked/value assignment.
                        keyboard_pair('forehand_hand', 'CA', 'C10')
                        case['focus'] = cdp.evaluate('(()=>{let e=document.activeElement,s=getComputedStyle(e.closest("label"));return {value:e.value,checked:e.checked,outline:s.outlineWidth,shadow:s.boxShadow}})()')
                        assert float(case['focus']['outline'].removesuffix('px')) > 0
                        cdp.screenshot(args.output / f"{case['name']}-selected-focus.png")
                        assert snapshot(server.app_context) == before and not counts
                        checkpoint('rejection')
                        submit('#workflow-form button[type="submit"]', pointer=script)
                        assert case['posts'][-1]['status'] == 400
                        assert checked('forehand_hand') == ['CA', 'C10']
                        case['rejection_focus'] = cdp.evaluate('({tag:document.activeElement.tagName,classes:document.activeElement.className})')
                        # Error links remain real fragment destinations.
                        href = cdp.evaluate('document.querySelector(".error-summary a").getAttribute("href")')
                        click(cdp, '.error-summary a')
                        case['error_target'] = cdp.evaluate('({hash:location.hash,id:document.activeElement.id,name:document.activeElement.name})')
                        assert case['error_target']['hash'] == href
                        checkpoint('language')
                        other = 'en' if locale == 'de' else 'de'
                        submit(f'.language-selector button[value="{other}"]')
                        assert checked('forehand_hand') == ['CA', 'C10']
                        checkpoint('correction')
                        for field, cards in DEAL.items():
                            if field != 'forehand_hand':
                                keyboard_pair(field, 'CA', 'C10')
                            select(field, cards)
                        assert not counts
                        submit('#workflow-form button[type="submit"]')
                        assert server.app_context.review_state.draft.step == 3
                        assert tuple(p.initial_hand for p in server.app_context.review_state.draft.players) == tuple(DEAL.values())[:3]
                        submit('#workflow-form button[type="submit"]')
                        assert server.app_context.review_state.draft.step == 4
                        cdp.screenshot(args.output / f"{case['name']}-discards-initial.png")
                        measure(case, 'discards')
                        assert cdp.evaluate('[...document.querySelectorAll("input[name=discarded_cards]")].map(e=>e.value)') == [c for c in CARDS if c in (*DEAL['forehand_hand'], *DEAL['skat'])]
                        keyboard_pair('discarded_cards', 'CA', 'C10')
                        select('discarded_cards', ['CA'])
                        submit('#workflow-form button[type="submit"]')
                        assert case['posts'][-1]['status'] == 400 and checked('discarded_cards') == ['CA']
                        select('discarded_cards', DEAL['skat'])
                        submit('#workflow-form button[type="submit"]')
                        assert server.app_context.review_state.draft.step == 5
                        submit('form[action="/actions/review/back"] button')
                        assert checked('discarded_cards') == list(DEAL['skat'])
                        submit('form[action="/actions/review/back"] button')
                        click(cdp, 'input[name="hand_game"]')
                        submit('#workflow-form button[type="submit"]')
                        assert not cdp.evaluate('!!document.querySelector("input[name=discarded_cards]")')
                        cdp.screenshot(args.output / f"{case['name']}-hand-exception.png")
                        submit('#workflow-form button[type="submit"]')
                        assert server.app_context.review_state.draft.discarded_cards == ()
                        checkpoint('passive-analysis')
                        before = snapshot(server.app_context)
                        cdp.navigate(server.origin + '/analyze')
                        cdp.screenshot(args.output / f"{case['name']}-analysis-initial.png")
                        measure(case, 'analysis')
                        for field, cards in {'hand': ['CA', 'CJ'], 'skat': ['D7'], 'public_declarer_cards': ['HA']}.items():
                            keyboard_pair(field, 'CA', 'C10')
                            select(field, cards)
                        assert snapshot(server.app_context) == before and not counts
                        checkpoint('analysis-rejection')
                        submit('#workflow-form button[type="submit"]')
                        assert case['posts'][-1]['status'] == 400
                        for field, number in (('hand', 2), ('skat', 1), ('public_declarer_cards', 1)):
                            assert str(number) in cdp.evaluate(f'document.querySelector("[data-validation-card-count={field}]").textContent')
                        target = cdp.evaluate('document.querySelector(".error-summary a").getAttribute("href").slice(1)')
                        click(cdp, '.error-summary a')
                        assert cdp.evaluate('document.activeElement.id') == target
                        checkpoint('language')
                        submit(f'.language-selector button[value="{locale}"]')
                        assert checked('hand') == ['CA', 'CJ']
                        if script:
                            select('hand', ['C10', 'D7'])
                            select('skat', [])
                            submit(f'.language-selector button[value="{other}"]')
                            assert checked('hand') == ['C10', 'D7'] and checked('skat') == []
                        checkpoint('explicit-analysis')
                        select('hand', CARDS[:10])
                        select('skat', [])
                        select('public_declarer_cards', [])
                        # Small explicit sample setting for the deliberate execution fixture.
                        click(cdp, 'details:has(input[name="sample_count"]) > summary')
                        click(cdp, 'input[name="sample_count"]')
                        cdp.call('Input.dispatchKeyEvent', type='keyDown', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=2)
                        cdp.call('Input.dispatchKeyEvent', type='keyUp', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=2)
                        cdp.call('Input.insertText', text='1')
                        submit('#workflow-form button[type="submit"]')
                        assert server.app_context.analyze_state.latest_successful_result is not None
                        assert counts['analysis'] == 1
                        checkpoint('passive-downloads')
                        state = server.app_context.analyze_state
                        assert http.request('GET', '/downloads/analyze/request.json')[2] == state.request_json_bytes
                        assert http.request('GET', '/downloads/analyze/result.json')[2] == state.result_json_bytes
                        assert not counts
                        checkpoint('session-fixture')
                        create_live(http)
                        checkpoint('passive-session')
                        before = snapshot(server.app_context)
                        cdp.navigate(server.origin + '/sessions/current')
                        cdp.screenshot(args.output / f"{case['name']}-session-initial.png")
                        measure(case, 'session', widths=(1365, 320))
                        assert cdp.evaluate('[...document.querySelectorAll(".compact-cards input")].slice(0,8).map(e=>e.value)') == ['CJ', 'CA', 'C10', 'CK', 'CQ', 'C9', 'C8', 'C7']
                        keyboard_pair('cards', 'CJ', 'CA')
                        assert snapshot(server.app_context) == before and not counts
                        checkpoint('complete')
                finally:
                    try:
                        next(fixture)
                    except StopIteration:
                        pass
        report['completed'] = True
        report['layout_summary'] = [{
            'case': m['case'], 'locale': m['locale'], 'stage': m['stage'],
            'viewport': m['width'], 'client': m['client'],
            'palettes': [{'name': p['name'], 'suit_width': p['groups'][0]['width'],
                          'rows': [len(row) for row in p['groups'][0]['rows']]}
                         for p in m['palettes']],
        } for m in report['measurements']]
    finally:
        local.close()
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'completed': report['completed'], 'cases': len(report['cases']),
                      'measurements': len(report['measurements']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
