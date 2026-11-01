# ruff: noqa: E501 - Keep browser expressions together.
"""Issue #306 bounded source-tree browser verification with disposable synthetic data."""

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
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests'), str(ROOT)]

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_card_palettes import DEAL, DEAL_ACTION, deal_page  # noqa: E402
from test_language_switch_context import switch  # noqa: E402
from test_manual_review_deal_validation import REPORTED, assert_count_rejection  # noqa: E402
from test_manual_review_saved_names import snapshot  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402
from verify_recording_deletion import click, focus, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.guided_rendering as rendering  # noqa: E402
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.app_web.workflow_operations as operations  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    assert Path(rendering.__file__).resolve().is_relative_to(ROOT / 'src')
    local = LocalBrowser(args.browser, args.output / 'browser-profile')
    cdp = local.cdp
    report = {'completed': False, 'python': sys.version, 'browser': local.version,
              'source': rendering.__file__, 'cases': [], 'resources': {},
              'zoom_boundary': 'CSS viewport resizing at actual 100% browser zoom; not enlarged-zoom evidence.'}
    for name in ('historical_deal_feedback.py', 'historical_form.py', 'historical_form_parsing.py',
                 'form_parsing.py', 'form_registry.py', 'validation_mapping.py', 'guided_rendering.py',
                 'assets/app.css', 'assets/workflow.js', 'locales/de.json', 'locales/en.json'):
        report['resources'][name] = hashlib.sha256((Path(rendering.__file__).parent / name).read_bytes()).hexdigest()

    def submit(case, selector):
        before = len(case['posts'])
        tab_to(cdp, selector)
        keyboard(cdp, 'Enter', 'Enter', 13, '\r')
        for _ in range(100):
            if len(case['posts']) > before:
                break
            time.sleep(.1)
        else:
            raise AssertionError(('No POST', selector))
        time.sleep(.4)
        return case['posts'][-1]

    def delivered(directory, stage):
        cdp.evaluate('void 0')
        event = next(e for e in reversed(cdp.events) if e['params'].get('type') == 'Document')
        raw = cdp.call('Network.getResponseBody', requestId=event['params']['requestId'])
        assert not raw.get('base64Encoded')
        (directory / (stage + '.html')).write_text(raw['body'], encoding='utf-8')
        return raw['body']

    def selections():
        return cdp.evaluate('Object.fromEntries([...document.querySelectorAll(".card-palette")].map(g=>[g.dataset.validationGroup,[...g.querySelectorAll("input:checked")].map(e=>e.value)]))')

    def inspect(case, directory, locale, stage):
        for width in (1365, 520, 320):
            cdp.call('Emulation.setDeviceMetricsOverride', width=width, height=900, deviceScaleFactor=1, mobile=False)
            time.sleep(.1)
            data = cdp.evaluate('''(()=>{const p=document.querySelector('#field-rearhand_hand'),s=document.querySelector('.error-summary');return {width:innerWidth,document:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,dpr:devicePixelRatio,scale:visualViewport.scale,summaryOverflow:s.scrollWidth>s.clientWidth+1,inlineOverflow:[...document.querySelectorAll('.field-error')].some(e=>e.scrollWidth>e.clientWidth+1),captions:[...document.querySelectorAll('.card-palette>p:not(.field-error)')].map(e=>e.textContent),groups:[...p.querySelectorAll('.compact-card-group')].map(g=>{const rows=new Map();for(const l of g.querySelectorAll('label')){let y=l.getBoundingClientRect().y;rows.set(y,(rows.get(y)||0)+1)}return [...rows.values()]}),tiles:[...p.querySelectorAll('label')].map(l=>({overflow:l.scrollWidth>l.clientWidth+1,font:getComputedStyle(l).fontSize,height:l.getBoundingClientRect().height,input:l.querySelector('input').getBoundingClientRect().width}))}})()''')
            data.update(stage=stage, zoom=cdp.call('Page.getLayoutMetrics')['cssVisualViewport'].get('zoom'))
            assert data['zoom'] == data['dpr'] == data['scale'] == 1
            assert data['document'] == data['client'] and not data['summaryOverflow'] and not data['inlineOverflow']
            assert data['captions'] == [text(locale, 'guided.review.cards_required', count=n) for n in (10, 10, 10, 2)]
            for rows in data['groups']:
                assert rows == ([8] if width == 1365 else [4, 4] if width == 520 else [2, 2, 2, 2])
            assert all(not t['overflow'] and t['font'] == '16px' and t['height'] >= 44 and t['input'] == 20 for t in data['tiles'])
            case['measurements'].append(data)
            for target, selector in (('error-summary', '.error-summary'),
                                     ('field-rearhand_hand', '#field-rearhand_hand'),
                                     ('inline-error', '#field-rearhand_hand .field-error')):
                cdp.evaluate('document.querySelector(' + json.dumps(selector) + ').scrollIntoView({block:"start"})')
                cdp.screenshot(directory / f'{stage}-{target}-{width}.png')

    try:
        for locale in ('de', 'en'):
            for script in (False, True):
                directory = args.output / f'{locale}-{script}'
                directory.mkdir()
                fixture = localized_server.__wrapped__(directory)
                server = next(fixture)
                context = server.app_context
                case = {'locale': locale, 'javascript': script, 'phase': 'fixture', 'posts': [],
                        'phases': {}, 'measurements': []}
                report['cases'].append(case)
                counts = Counter()
                real_replace, real_response = os.replace, Handler.send_response

                def replaced(source, destination, counts=counts, real=real_replace, server=server):
                    if Path(destination).is_relative_to(server.app_context.managed_home.root):
                        counts['persistent_replacements'] += 1
                    return real(source, destination)

                def responded(handler, status, *a, case=case, real=real_response, **kw):
                    if handler.command == 'POST':
                        case['posts'].append({'phase': case['phase'], 'path': handler.path, 'status': status})
                    return real(handler, status, *a, **kw)

                def counted(label, real, counts=counts):
                    def call(*a, **kw):
                        counts[label] += 1
                        return real(*a, **kw)
                    return call

                def checkpoint(next_phase, case=case, counts=counts):
                    assert not any(counts[key] for key in ('analysis', 'review', 'learning_preparation'))
                    if case['phase'].startswith('passive') or case['phase'] in {'rejection', 'correction'}:
                        assert not counts
                    if case['phase'].startswith('passive'):
                        assert not any(p['phase'] == case['phase'] for p in case['posts'])
                    case['phases'][case['phase']] = dict(counts)
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
                        ):
                            stack.enter_context(patch.object(module, attr, counted(label, getattr(module, attr))))
                        http = Browser(server)
                        switch(http, deal_page(http), locale)
                        state, files = context.review_state, snapshot(context)
                        case['initial_revision'] = state.revision
                        cdp.call('Network.setCookie', name=http.cookie.split('=', 1)[0], value=http.cookie.split('=', 1)[1], url=server.origin, httpOnly=True, sameSite='Strict')
                        cdp.call('Emulation.setScriptExecutionDisabled', value=not script)
                        cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
                        cdp.navigate(server.origin + '/review')
                        delivered(directory, 'initial')
                        for route, name in (('/assets/app.css', 'assets/app.css'), ('/matches/assets/capture.js', 'assets/workflow.js')):
                            status, _, raw = http.request('GET', route)
                            assert status == 200 and hashlib.sha256(raw).hexdigest() == report['resources'][name]
                        checkpoint('passive-selection')
                        event_count = len(cdp.events)
                        for field, cards in REPORTED.items():
                            for card in cards:
                                click(cdp, f'input[name="{field}"][value="{card}"]')
                        assert selections() == {k: list(v) for k, v in REPORTED.items()}
                        captions = cdp.evaluate('[...document.querySelectorAll(".card-palette>p")].map(e=>e.textContent)')
                        assert captions == [text(locale, 'guided.review.cards_required', count=n) for n in (10, 10, 10, 2)]
                        assert len(cdp.events) == event_count and context.review_state is state
                        assert snapshot(context) == files
                        checkpoint('rejection')
                        assert submit(case, f'form[action="{DEAL_ACTION}"] button')['status'] == 400
                        # Capture before verifier scrolling, focusing or layout probes.
                        cdp.screenshot(directory / 'rejection-initial.png')
                        case['initial_error_focus'] = focus(cdp)
                        assert case['initial_error_focus']['tag'] == 'SECTION'
                        assert cdp.evaluate('document.activeElement.className') == 'error-summary'
                        raw = delivered(directory, 'rejection')
                        assert_count_rejection(raw, locale, REPORTED, 'rearhand_hand', 10)
                        assert context.review_state is state and snapshot(context) == files
                        checkpoint('passive-error-navigation')
                        tab_to(cdp, '.error-summary a')
                        keyboard(cdp, 'Enter', 'Enter', 13, '\r')
                        case['group_focus'] = focus(cdp)
                        assert case['group_focus']['id'] == 'field-rearhand_hand'
                        assert case['group_focus']['visible'] and case['group_focus']['width'] != '0px'
                        cdp.screenshot(directory / 'error-link-keyboard.png')
                        assert selections() == {k: list(v) for k, v in REPORTED.items()}
                        inspect(case, directory, locale, 'rejection')
                        assert snapshot(context) == files
                        checkpoint('native-language')
                        other = 'en' if locale == 'de' else 'de'
                        cdp.call('Emulation.setScriptExecutionDisabled', value=True)
                        assert submit(case, f'.language-selector button[value="{other}"]')['status'] == 303
                        assert_count_rejection(delivered(directory, 'native-language'), other, REPORTED, 'rearhand_hand', 10, initial=False)
                        assert context.review_state is state
                        checkpoint('passive-language')
                        files = snapshot(context)
                        inspect(case, directory, other, 'native-language')
                        assert snapshot(context) == files
                        checkpoint('enhanced-language' if script else 'native-language-back')
                        cdp.call('Emulation.setScriptExecutionDisabled', value=not script)
                        if script:
                            cdp.navigate(server.origin + '/review')
                        assert submit(case, f'.language-selector button[value="{locale}"]')['status'] == 303
                        assert_count_rejection(delivered(directory, 'language-back'), locale, REPORTED, 'rearhand_hand', 10, initial=False)
                        request = next(e['params']['request'] for e in reversed(cdp.events) if e['params']['request']['method'] == 'POST')
                        values = parse_qs(request.get('postData', ''))
                        assert ('_frontend_language_values' in values) == script
                        case['enhanced_envelope_present'] = '_frontend_language_values' in values
                        assert context.review_state is state
                        checkpoint('passive-correction-selection')
                        files = snapshot(context)
                        click(cdp, 'input[name="rearhand_hand"][value="H7"]')
                        assert selections() == {k: list(v) for k, v in DEAL.items()}
                        assert context.review_state is state and snapshot(context) == files
                        checkpoint('correction')
                        assert submit(case, f'form[action="{DEAL_ACTION}"] button')['status'] == 303
                        assert context.review_state.draft.step == 3
                        assert context.review_state.revision == state.revision + 1
                        assert tuple(p.initial_hand for p in context.review_state.draft.players) == tuple(DEAL.values())[:3]
                        assert context.review_state.draft.skat == DEAL['skat']
                        assert snapshot(context) == files
                        case['final_revision'] = context.review_state.revision
                        delivered(directory, 'accepted-step-3')
                        cdp.screenshot(directory / 'accepted-step-3.png')
                        checkpoint('complete')
                finally:
                    try:
                        next(fixture)
                    except StopIteration:
                        pass
        report['completed'] = True
        report['operations'] = dict(sum((Counter(v) for c in report['cases'] for v in c['phases'].values()), Counter()))
        report['posts'] = dict(Counter(f"{p['status']} {p['path']}" for c in report['cases'] for p in c['posts']))
    finally:
        local.close()
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'completed': report['completed'], 'cases': len(report['cases']),
                      'operations': report.get('operations'), 'posts': report.get('posts'),
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
