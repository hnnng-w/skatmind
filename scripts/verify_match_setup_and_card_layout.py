# ruff: noqa: E501 - Keep browser expressions legible.
"""Disposable native-browser Issue #294 reproduction and regression evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.resources
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
if '--baseline-archive' in sys.argv:
    sys.path.insert(0, sys.argv[sys.argv.index('--baseline-archive') + 1] + '/src')

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_compact_play_grid_web import start_play  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402
from test_match_setup_and_card_layout import saved_players  # noqa: E402
from test_session_declaration_correction_web import select as correction_editor  # noqa: E402
from test_session_direct_card_start_web import create as create_session  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402
from verify_recording_deletion import click, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.match_frontend as frontend  # noqa: E402
import skatmind.app_web.profile_driven_creation as creation  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('before', 'after'), required=True)
    parser.add_argument('--baseline-archive', type=Path)
    parser.add_argument('--scope', choices=('all', 'layout', 'supplement'), default='all')
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    started_at = time.perf_counter()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / 'browser-profile')
    cdp = local.cdp
    report = {'completed': False, 'phase': args.phase, 'python': sys.version,
              'browser': local.version, 'cases': [], 'measurements': [],
              'loaded_module': frontend.__file__,
              'resources': {name: hashlib.sha256(importlib.resources.files('skatmind.app_web')
                  .joinpath(name).read_bytes()).hexdigest() for name in
                  ('assets/app.css', 'assets/workflow.js', 'locales/en.json', 'locales/de.json')},
              'scope': 'source-tree developer evidence; disposable data',
              'zoom': 'Fresh profile 100%; actual 200% browser zoom pending. Viewport emulation is not zoom.'}
    counts = Counter()
    replace = os.replace
    operation = frontend.apply_unified_match_operation_v1
    save_profile = profile.save_frontend_profile_file_v1
    send_response = Handler.send_response
    responses = []

    def responded(handler, status, *args, **kwargs):
        if handler.command == 'POST':
            responses.append({'path': handler.path, 'status': int(status)})
        return send_response(handler, status, *args, **kwargs)

    def replaced(source, destination):
        if Path(destination).parent == server.app_context.managed_stateful.root('matches'):
            counts['recording_writes'] += 1
        return replace(source, destination)

    def operated(active, values):
        counts[values['operation']] += 1
        return operation(active, values)

    def profiled(*a, **kw):
        counts['profile_writes'] += 1
        return save_profile(*a, **kw)

    def choose(name, *, label=None, value=None):
        selector = f'select[name="{name}"]'
        index = cdp.evaluate('[...document.querySelector(' + json.dumps(selector) + ').options].findIndex(o=>' +
                             ('o.textContent.startsWith(' + json.dumps(label) + ')' if label else
                              'o.value===' + json.dumps(value)) + ')')
        assert index >= 0, (name, label, value)
        # Focus the real native control without opening Edge's headless popup.
        cdp.evaluate('document.querySelector(' + json.dumps(selector) + ').scrollIntoView({block:"center"});document.querySelector(' + json.dumps(selector) + ').focus()')
        keyboard(cdp, 'Home', 'Home', 36)
        for _ in range(index):
            keyboard(cdp, 'ArrowDown', 'ArrowDown', 40)
        keyboard(cdp, 'Tab', 'Tab', 9)
        assert cdp.evaluate('document.querySelector(' + json.dumps(selector) + ').selectedIndex') == index

    def submit(selector, *, pointer=False):
        if pointer:
            click(cdp, selector)
        else:
            tab_to(cdp, selector)
            keyboard(cdp, 'Enter', 'Enter', 13, '\r')
        time.sleep(.65)

    def enter(name, value):
        click(cdp, f'input[name="{name}"]')
        cdp.call('Input.dispatchKeyEvent', type='keyDown', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=2)
        cdp.call('Input.dispatchKeyEvent', type='keyUp', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=2)
        keyboard(cdp, 'Backspace', 'Backspace', 8)
        if value:
            cdp.call('Input.insertText', text=value)

    def controls():
        return cdp.evaluate("[...document.querySelectorAll('.seat-setup select,.seat-setup input[name=perspective_seat],.seat-setup button,#match-declaration select,.declaration-checks input')].map(e=>({name:e.name,value:e.value,options:e.options?[...e.options].map(o=>({value:o.value,label:o.textContent})):null}))")

    def posts():
        cdp.evaluate('void 0')
        return [e['params']['request'] for e in cdp.events if e['params']['request']['method'] == 'POST']

    def counted(name, real):
        def call(*args, **kwargs):
            counts[name] += 1
            return real(*args, **kwargs)
        return call

    def measure(case, name):
        # Open the actual native disclosures with pointer input.
        for field in ('evidence_perspective_hand', 'evidence_original_skat'):
            summaries = cdp.evaluate("(()=>{let e=document.querySelector('[name=" + field + "]');let a=[];while(e){if(e.tagName==='DETAILS'&&!e.open){let s=e.querySelector('summary');s.id='probe-open-" + field + "-'+a.length;a.push('#'+s.id)}e=e.parentElement}return a.reverse()})()")
            for selector in summaries:
                click(cdp, selector)
        for width, height in ((1365, 900), (1920, 1000), (2560, 1000),
                              (1030, 900), (1050, 900), (1180, 900), (1220, 900),
                              (520, 844), (320, 800)):
            cdp.call('Emulation.setDeviceMetricsOverride', width=width, height=height, deviceScaleFactor=1, mobile=False)
            time.sleep(.1)
            data = cdp.evaluate("""(()=>{const palettes=[...document.querySelectorAll('.compact-cards')].filter(e=>e.getBoundingClientRect().height);return {width:innerWidth,dpr:devicePixelRatio,scale:visualViewport.scale,document:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,palettes:palettes.map(e=>({name:e.querySelector('input').name,groups:[...e.querySelectorAll('.compact-card-group')].map(g=>{const rows=new Map();for(const l of g.querySelectorAll('.compact-card')){const r=l.getBoundingClientRect();const y=Math.round(r.y*10)/10;if(!rows.has(y))rows.set(y,[]);rows.get(y).push(l.querySelector('input').value)}return {rows:[...rows.values()],width:g.getBoundingClientRect().width}}),tiles:[...e.querySelectorAll('.compact-card')].map(l=>{const r=l.getBoundingClientRect(),i=l.querySelector('input').getBoundingClientRect();return {width:r.width,height:r.height,font:getComputedStyle(l).fontSize,input:i.width,overflow:l.scrollWidth>l.clientWidth+1}})}))}})()""")
            data.update(case=case, stage=name)
            data['ancestors'] = cdp.evaluate("[...document.querySelectorAll('.compact-cards')].filter(e=>e.checkVisibility()).map(e=>{const a=[];let p=e;while(p){const s=getComputedStyle(p),r=p.getBoundingClientRect();a.push({tag:p.tagName,id:p.id,classes:p.className,width:r.width,font:s.fontSize,columns:s.gridTemplateColumns,padding:s.padding});if(p.tagName==='MAIN')break;p=p.parentElement}return {name:e.querySelector('input').name,ancestors:a}})")
            data['browser_zoom'] = cdp.call('Page.getLayoutMetrics')['cssVisualViewport'].get('zoom')
            assert data['browser_zoom'] == 1, 'Expected actual 100% browser zoom.'
            report['measurements'].append(data)
            if not case.startswith('session-'):
                expected = {'evidence_perspective_hand', 'evidence_original_skat', 'evidence_discarded_cards'}
                if name != 'evidence':
                    expected.add('cards')
                    assert cdp.evaluate("document.querySelector('#match-recording [data-recorded-summary]').checkVisibility()")
                assert {p['name'] for p in data['palettes']} == expected
                for palette in data['palettes']:
                    offered = [suit + rank for suit in 'CSHD' for rank in ('J', 'A', '10', 'K', 'Q', '9', '8', '7')
                               if not (palette['name'] == 'cards' and name == 'sparse-play' and suit + rank == 'CA')]
                    assert [card for group in palette['groups'] for row in group['rows'] for card in row] == offered
            if args.phase == 'after':
                if data['document'] != data['client']:
                    data['overflowing'] = cdp.evaluate("[...document.querySelectorAll('main *')].filter(e=>e.checkVisibility()&&e.getBoundingClientRect().right>document.documentElement.clientWidth+1).map(e=>({tag:e.tagName,classes:e.className,name:e.name,text:e.textContent.slice(0,160),right:e.getBoundingClientRect().right}))")
                assert data['document'] == data['client'], data.get('overflowing')
                for palette in data['palettes']:
                    assert all(not tile['overflow'] and tile['height'] >= 44 for tile in palette['tiles'])
                    assert all(tile['font'] == '16px' and tile['input'] == 20 for tile in palette['tiles'])
                    for group in palette['groups']:
                        if sum(map(len, group['rows'])) == 8:
                            assert [len(row) for row in group['rows']] in ([8], [4, 4], [2]*4, [1]*8), group
            # Each selector is captured at its own scroll position, including focus.
            for field in ('evidence_perspective_hand', 'evidence_original_skat', 'evidence_discarded_cards', 'cards'):
                selector = f'.compact-cards input[name="{field}"]'
                if cdp.evaluate('!!document.querySelector(' + json.dumps(selector) + ')'):
                    assert cdp.evaluate('document.querySelector(' + json.dumps(selector) + ').checkVisibility()')
                    cdp.evaluate('document.querySelector(' + json.dumps(selector) + ').scrollIntoView({block:"center"});document.querySelector(' + json.dumps(selector) + ').focus()')
                    data.setdefault('focus', {})[field] = cdp.evaluate("(()=>{const e=document.activeElement,l=e.closest('label'),s=getComputedStyle(l);return {name:e.name,value:e.value,outline:s.outlineWidth,offset:s.outlineOffset,visible:e.checkVisibility()}})()")
                    time.sleep(.2)
                    cdp.screenshot(args.output / f'{case}-{name}-{width}-{field}.png')
            if args.phase == 'after' and width >= 1365 and not case.startswith('session-'):
                for palette in data['palettes']:
                    for group in palette['groups']:
                        if sum(map(len, group['rows'])) == 8:
                            assert len(group['rows']) == 1, (palette['name'], width, group)

    try:
        http = Browser(server)
        saved_players(http)
        cdp.call('Network.setCookie', name=http.cookie.split('=', 1)[0], value=http.cookie.split('=', 1)[1], url=server.origin, httpOnly=True, sameSite='Strict')
        with ExitStack() as stack:
            stack.enter_context(patch.object(os, 'replace', replaced))
            stack.enter_context(patch.object(frontend, 'apply_unified_match_operation_v1', operated))
            stack.enter_context(patch.object(profile, 'save_frontend_profile_file_v1', profiled))
            stack.enter_context(patch.object(Handler, 'send_response', responded))
            stack.enter_context(patch.object(creation, 'generate_frontend_match_id_v1',
                counted('match_ids', creation.generate_frontend_match_id_v1)))
            stack.enter_context(patch.object(creation, 'generate_frontend_player_id_v1',
                counted('player_ids', creation.generate_frontend_player_id_v1)))
            cases = [(locale, script, 'saved') for locale, script in
                     (('en', False), ('de', False), ('en', True), ('de', True))]
            if args.scope == 'supplement':
                cases = []
            if args.phase == 'after' and args.scope != 'layout':
                cases += [('en', False, 'new'), ('de', True, 'new'),
                          ('de', False, 'mixed'), ('en', True, 'mixed'),
                          ('en', False, 'own'), ('de', True, 'own'),
                          ('en', True, 'manual-own'), ('de', False, 'manual-own')]
            for locale, script, roster in cases:
                if roster == 'own':
                    page = http.page('/settings')
                    from test_match_setup_and_card_layout import options
                    own = next(value for value, label in options(page, 'own_player_handle') if label == 'Anna')
                    follow(http, http.submit(Forms(page).find('/actions/profile/preferences'), own_player_handle=own))
                page = http.page('/matches/new')
                follow(http, http.submit(Forms(page).find('/actions/profile/language'), language=locale))
                cdp.call('Emulation.setScriptExecutionDisabled', value=not script)
                cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
                cdp.navigate(server.origin + '/matches/new')
                counts.clear()
                cdp.events.clear()
                case = {'locale': locale, 'script': script, 'roster': roster, 'initial': controls()}
                report['cases'].append(case)
                click(cdp, 'input[name=match_title]')
                cdp.call('Input.insertText', text='Synthetic Match 294')
                if roster == 'manual-own':
                    choose('perspective_mode', value='manual')
                if roster == 'own':
                    choose('rearhand_handle', label='Clara')
                    choose('own_seat', value='rearhand')
                    choose('forehand_handle', label='Bea')
                    choose('middlehand_handle', label='Clara')
                else:
                    for seat, label in zip(('forehand', 'middlehand', 'rearhand'), ('Anna', 'Bea', 'Clara'), strict=True):
                        if roster == 'new' or (roster == 'mixed' and seat == 'forehand'):
                            choose(seat + '_mode', value='new')
                            click(cdp, f'input[name="{seat}_name"]')
                            cdp.call('Input.insertText', text={'Anna': 'Dora', 'Bea': 'Eve', 'Clara': 'Fay'}[label])
                        else:
                            choose(seat + '_handle', label=label)
                assert counts == Counter()
                assert not any(e['params']['request']['method'] == 'POST' for e in cdp.events)
                selected_seat = 'forehand' if roster == 'new' else 'rearhand' if roster == 'mixed' else 'middlehand'
                if args.phase == 'after' and roster != 'own':
                    action = 'choose_' + selected_seat
                else:
                    action = 'update'
                case['activation'] = 'pointer' if script else 'Tab/Enter'
                case['filled_before_submission'] = controls()
                if action.startswith('choose_'):
                    selector = f'button[name=setup_action][value={action}]'
                    case['setup_layouts'] = []
                    for width in (1365, 520, 320):
                        cdp.call('Emulation.setDeviceMetricsOverride', width=width, height=900, deviceScaleFactor=1, mobile=False)
                        tab_to(cdp, selector)
                        cdp.evaluate('document.activeElement.scrollIntoView({block:"center"})')
                        time.sleep(.2)
                        geometry = cdp.evaluate("(()=>{const e=document.activeElement,r=e.getBoundingClientRect(),s=getComputedStyle(e);return {width:innerWidth,document:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,button_width:r.width,button_height:r.height,outline:s.outlineWidth,overflow:e.scrollWidth>e.clientWidth+1}})()")
                        assert geometry['document'] == geometry['client'] and not geometry['overflow']
                        assert geometry['button_height'] >= 44
                        assert float(geometry['outline'].removesuffix('px')) > 0
                        case['setup_layouts'].append(geometry)
                        cdp.screenshot(args.output / f'{locale}-{script}-{roster}-person-action-focus-{width}.png')
                submit(f'button[name=setup_action][value={action}]' + (':not([hidden])' if action == 'update' else ''), pointer=script)
                if roster == 'own':
                    assert cdp.evaluate("!!document.querySelector('.error-summary')")
                    assert not counts
                    choose('rearhand_handle', label='Anna')
                    submit('button[name=setup_action][value=update]:not([hidden])')
                case['roster_update'] = controls()
                case['roster_error'] = cdp.evaluate("!!document.querySelector('.error-summary')")
                case['update_counts'] = dict(counts)
                assert counts == Counter()
                assert case['roster_error'] == (args.phase == 'before')
                if args.phase == 'after':
                    # Issue #297: capture the actual delivery before any verifier scrolling.
                    landing = cdp.evaluate("(()=>{const e=document.querySelector('#match-setup-review'),b=document.querySelector('button[value=create]');const r=e.getBoundingClientRect(),s=b.getBoundingClientRect();return {text:e.textContent,focus:document.activeElement.id,reviewTop:r.top,reviewBottom:r.bottom,createTop:s.top,createBottom:s.bottom,height:innerHeight}})()")
                    case['review_initial_landing'] = landing
                    cdp.screenshot(args.output / f'{locale}-{script}-{roster}-review-initial-landing.png')
                    assert landing['focus'] == 'match-setup-review'
                    assert 0 <= landing['reviewTop'] < landing['reviewBottom'] <= landing['height']
                    assert 0 <= landing['createTop'] < landing['createBottom'] <= landing['height']
                    keyboard(cdp, 'Tab', 'Tab', 9)
                    assert cdp.evaluate("document.activeElement.name==='setup_action'&&document.activeElement.value==='create'")
                cdp.evaluate("document.querySelector('.seat-setup').scrollIntoView({block:'start'})")
                time.sleep(.2)
                cdp.screenshot(args.output / f'{locale}-{script}-{roster}-roster.png')
                perspective = 'Anna' if roster == 'own' else 'Dora' if roster == 'new' else 'Clara' if roster == 'mixed' else 'Bea'
                if args.phase == 'after':
                    assert landing['text'].endswith(': ' + perspective)
                if args.phase == 'before':
                    choose('perspective_seat', value='middlehand')
                    submit('button[name=setup_action][value=update]')
                elif roster != 'own':
                    assert len(posts()) == 1
                    assert parse_qs(posts()[0]['postData'])['setup_action'] == [action]
                    assert cdp.evaluate("!!document.querySelector('button[name=setup_action][value=create]')")
                    case['first_review_posts'] = 1
                if args.phase == 'after':
                    assert not cdp.evaluate("!!document.querySelector('select[name=perspective_seat]')")
                assert counts == Counter()
                if roster in {'new', 'mixed'}:
                    original_choice = cdp.evaluate("document.querySelector('[name=perspective_seat]').value")
                    if roster == 'new':
                        enter('forehand_name', 'Fay')
                        enter('rearhand_name', 'Dora')
                        replaced_seat = 'rearhand'
                    else:
                        choose('middlehand_handle', label='Clara')
                        choose('rearhand_handle', label='Bea')
                        replaced_seat = 'middlehand'
                    submit('button[name=setup_action][value=update]:not([hidden])')
                    assert cdp.evaluate("document.querySelector('[name=perspective_seat]').value") == original_choice
                    if roster == 'mixed':
                        choose(replaced_seat + '_handle', value='')
                        choose(replaced_seat + '_mode', value='new')
                    enter(replaced_seat + '_name', 'Gina')
                    submit('button[name=setup_action][value=update]:not([hidden])')
                    assert cdp.evaluate("document.querySelector('[name=perspective_seat]').value") == ''
                    assert not cdp.evaluate("!!document.querySelector('button[name=setup_action][value=create]')")
                    assert not cdp.evaluate("!!document.querySelector('.error-summary')")
                    assert counts == Counter()
                    cdp.activate('.language-selector button[value="' + ('de' if locale == 'en' else 'en') + '"]')
                    assert cdp.evaluate("document.querySelector('[name=perspective_seat]').value") == ''
                    perspective = 'Eve' if roster == 'new' else 'Bea'
                    action = 'choose_middlehand' if roster == 'new' else 'choose_rearhand'
                    enter('source_url', 'not-a-url')
                    submit(f'button[name=setup_action][value={action}]', pointer=script)
                    assert cdp.evaluate("!!document.querySelector('.error-summary')")
                    selected = cdp.evaluate("document.querySelector('[name=perspective_seat]').value")
                    assert selected
                    cdp.activate('.language-selector button[value="' + locale + '"]')
                    assert cdp.evaluate("document.querySelector('[name=perspective_seat]').value") == selected
                    assert cdp.evaluate("document.querySelector('[name=source_url]').value") == 'not-a-url'
                    enter('source_url', '')
                    submit('button[name=setup_action][value=update]:not([hidden])')
                    assert counts['profile_writes'] == 2 and not counts['recording_writes']
                    assert not counts['match_ids'] and not counts['player_ids']
                    case['roster_replacement'] = controls()
                submit('button[name=setup_action][value=create]')
                active = server.app_context.managed_stateful.active_match
                definition = active.workspace.match_definition
                assert definition.perspective_player_id == next(p.player_id for p in definition.participants if p.player_label == perspective)
                if roster == 'manual-own':
                    assert definition.perspective_player_id != server.app_context.frontend_profile.document.own_player_id
                assert counts['recording_writes'] == 1
                assert counts['profile_writes'] == (3 if roster in {'new', 'mixed'} else 1)
                assert counts['match_ids'] == 1
                case['creation_counts'] = dict(counts)
                cdp.activate('form:has(input[name=operation][value=start_game]) button')
                case['declaration'] = controls()
                if roster == 'saved':
                    measure(f'{locale}-{script}', 'evidence')
                cdp.call('Emulation.setDeviceMetricsOverride', width=1365, height=900, deviceScaleFactor=1, mobile=False)
                choose('declarer_player_id', label=perspective)
                choose('game_type', value='grand')
                click(cdp, '#match-declaration input[name=bid_value]')
                cdp.call('Input.insertText', text='18')
                counts.clear()
                cdp.activate('#match-declaration button[value=set_declaration]')
                assert counts['set_declaration'] == counts['recording_writes'] == 1 and not counts['profile_writes']
                if roster == 'saved':
                    measure(f'{locale}-{script}', 'play')
                    if args.phase == 'after':
                        counts.clear()
                        selector = 'input[name="cards"][value="CA"]'
                        click(cdp, selector)
                        keyboard(cdp, 'Space', 'Space', 32, ' ')
                        assert counts == Counter()
                        assert cdp.evaluate('document.querySelector(' + json.dumps(selector) + ').checked')
                        submit('form:has(input[name="operation"][value="append_plays"]) button.primary')
                        assert counts['append_plays'] == counts['recording_writes'] == 1
                        assert not counts['profile_writes'] and not counts['set_declaration']
                        measure(f'{locale}-{script}', 'sparse-play')
                case['final_counts'] = dict(counts)
                case['submissions'] = [parse_qs(r.get('postData', ''), keep_blank_values=True) for r in posts()]
                case['requests'] = [e['params']['request']['url'].split(server.origin)[-1] for e in cdp.events if e['params']['request']['method'] == 'POST']
            if args.phase == 'after' and args.scope != 'layout':
                page = http.page('/settings')
                follow(http, http.submit(Forms(page).find('/actions/profile/preferences'), own_player_handle=''))
                for locale, script in (('en', False), ('de', False), ('en', True), ('de', True)):
                    page = http.page('/matches/new')
                    follow(http, http.submit(Forms(page).find('/actions/profile/language'), language=locale))
                    cdp.call('Emulation.setScriptExecutionDisabled', value=not script)
                    cdp.navigate(server.origin + '/matches/new')
                    for seat, label in zip(('forehand', 'middlehand', 'rearhand'), ('Anna', 'Bea', 'Clara'), strict=True):
                        choose(seat + '_mode', value='saved')
                        if cdp.evaluate(f"document.querySelector('input[name={seat}_name]').value"):
                            enter(seat + '_name', '')
                        choose(seat + '_handle', label=label)
                    counts.clear()
                    cdp.events.clear()
                    for field in ('match_title', 'forehand_name'):
                        if field == 'forehand_name':
                            choose('forehand_handle', value='')
                            choose('forehand_mode', value='new')
                        enter(field, 'Neutral title' if field == 'match_title' else 'Dora')
                        keyboard(cdp, 'Enter', 'Enter', 13, '\r')
                        time.sleep(.65)
                        assert parse_qs(posts()[-1]['postData'])['setup_action'] == ['update']
                        assert cdp.evaluate("document.querySelector('[name=perspective_seat]').value") == ''
                        assert not cdp.evaluate("!!document.querySelector('button[name=setup_action][value=create]')")
                        assert not counts
                    report.setdefault('neutral_enter', []).append({'locale': locale, 'script': script,
                        'submissions': [parse_qs(r['postData'], keep_blank_values=True) for r in posts()], 'counts': dict(counts)})
                # A genuine second browser changes perspective while the first keeps
                # its original reviewed Create control and hidden person binding.
                primary = cdp
                other_browser = LocalBrowser(args.browser, args.output / 'stale-create-browser')
                try:
                    cdp.navigate(server.origin + '/matches/new')
                    for seat, label in zip(('forehand', 'middlehand', 'rearhand'), ('Anna', 'Bea', 'Clara'), strict=True):
                        choose(seat + '_mode', value='saved')
                        if cdp.evaluate(f"document.querySelector('input[name={seat}_name]').value"):
                            enter(seat + '_name', '')
                        choose(seat + '_handle', label=label)
                    enter('match_title', 'Stale reviewed person')
                    counts.clear()
                    submit('button[name=setup_action][value=choose_middlehand]')
                    old_person = cdp.evaluate("document.querySelector('[name=perspective_seat]').value")
                    cdp = other_browser.cdp
                    cdp.call('Network.setCookie', name=http.cookie.split('=', 1)[0], value=http.cookie.split('=', 1)[1], url=server.origin, httpOnly=True, sameSite='Strict')
                    cdp.call('Emulation.setScriptExecutionDisabled', value=True)
                    cdp.navigate(server.origin + '/matches/new')
                    submit('button[name=setup_action][value=choose_rearhand]', pointer=True)
                    new_person = cdp.evaluate("document.querySelector('[name=perspective_seat]').value")
                    assert old_person != new_person
                    cdp = primary
                    submit('button[name=setup_action][value=create]')
                    assert responses[-1]['status'] == 400
                    assert cdp.evaluate("!!document.querySelector('.error-summary')")
                    assert not counts
                    cdp.screenshot(args.output / 'stale-create-rejected.png')
                    report['stale_create'] = {'status': 400, 'counts': dict(counts),
                        'old_person': old_person, 'new_person': new_person}
                finally:
                    cdp = primary
                    other_browser.close()
                # Briefly verify existing shared Session tracks and correction controls.
                page = http.page('/settings')
                # This Session fixture requires an empty synthetic directory.
                follow(http, http.submit(Forms(page).find('/actions/profile/reset'), confirm_reset='on'))
                for locale, script in (('en', True), ('de', False)):
                    cdp.call('Emulation.setScriptExecutionDisabled', value=not script)
                    page = http.page('/sessions')
                    follow(http, http.submit(Forms(page).find('/actions/profile/language'), language=locale))
                    create_session(http)
                    cdp.navigate(server.origin + '/sessions/current')
                    measure('session-' + locale, 'hand')
                    start_play(http, locale)
                    cdp.navigate(server.origin + '/sessions/current')
                    measure('session-' + locale, 'play')
                    correction_editor(http, 'set_declaration')
                    cdp.navigate(server.origin + '/sessions/current')
                    assert cdp.evaluate("[...document.querySelectorAll('.declaration-checks input')].map(e=>e.name)") == ['hand_game', 'schneider_announced', 'schwarz_announced', 'ouvert']
                    cdp.evaluate("document.querySelector('.declaration-checks').scrollIntoView({block:'center'})")
                    time.sleep(.2)
                    cdp.screenshot(args.output / f'session-{locale}-declaration.png')
                cdp.navigate(server.origin + '/matches/current')
                before_zoom = cdp.call('Page.getLayoutMetrics')['cssVisualViewport'].get('zoom')
                for _ in range(5):
                    cdp.call('Input.dispatchKeyEvent', type='keyDown', key='+', code='Equal', windowsVirtualKeyCode=187, modifiers=2)
                    cdp.call('Input.dispatchKeyEvent', type='keyUp', key='+', code='Equal', windowsVirtualKeyCode=187, modifiers=2)
                actual_zoom = cdp.call('Page.getLayoutMetrics')['cssVisualViewport'].get('zoom')
                report['zoom_shortcut_probe'] = {'before': before_zoom, 'requested': 2, 'actual': actual_zoom}
            report['post_responses'] = responses
            report['completed'] = True
    finally:
        report['elapsed_seconds'] = round(time.perf_counter() - started_at, 3)
        (args.output / 'evidence.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        table = [{'viewport': m['width'], 'document': m['document'], 'client': m['client'],
                  'zoom': m['browser_zoom'], 'palettes': {
                      p['name']: {'suit_width': p['groups'][0]['width'],
                                  'rows': [len(row) for row in p['groups'][0]['rows']]}
                      for p in m['palettes']}}
                 for m in report['measurements'] if m['case'] == 'en-False' and m['stage'] == 'play']
        (args.output / 'summary.json').write_text(json.dumps({
            'completed': report['completed'], 'seconds': report['elapsed_seconds'],
            'cases': len(report['cases']), 'measurements': len(report['measurements']),
            'wide_and_narrow_match_rows': table,
            'neutral_enter_cases': len(report.get('neutral_enter', [])),
            'stale_create': report.get('stale_create'),
            'zoom_shortcut_probe': report.get('zoom_shortcut_probe')}, indent=2), encoding='utf-8')
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({'completed': report['completed'], 'cases': len(report['cases']), 'measurements': len(report['measurements'])}))


if __name__ == '__main__':
    main()
