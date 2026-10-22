"""Issue #294: final HTTP controls, person-bound setup and narrow presentation opt-ins."""

import re
from html import unescape

import pytest
from test_direct_match_evidence import started
from test_frontend_language_switching import localized_server as _localized_server
from test_match_declaration_drafts import NativePage, create_replay_match
from test_match_recording_recovery_web import follow, operation_form
from test_session_recorded_review_web import Browser, Forms
from test_settings_seat_setup_web import player_action
from test_task_first_language_preservation import enhanced_switch, envelope


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def options(page, name):
    select = re.search(r'<select\b[^>]*name="' + name + r'"[^>]*>(.*?)</select>', page, re.S)
    return [(unescape(value), unescape(re.sub('<[^>]+>', '', label))) for value, label in
            re.findall(r'<option value="([^"]*)"[^>]*>(.*?)</option>', select[1], re.S)]


def saved_players(browser):
    page = browser.page('/settings')
    for name in ('Anna', 'Bea', 'Clara'):
        page = follow(browser, browser.submit(player_action(page, 'edit')))
        page = follow(browser, browser.submit(player_action(page, 'add'), display_name=name))
    return dict((label, value) for value, label in options(page, 'own_player_handle') if value)


def reviewed_roster(browser, *, saved=False):
    handles = saved_players(browser) if saved else {}
    page = browser.page('/matches/new')
    fields = {'match_title': 'Identity binding', 'setup_action': 'choose_middlehand'}
    for seat, name in zip(('forehand', 'middlehand', 'rearhand'),
                          ('Anna', 'Bea', 'Clara'), strict=True):
        fields[seat + ('_handle' if saved else '_name')] = handles[name] if saved else name
    page = follow(browser, browser.submit(Forms(page).find('/matches/api/v1/create'), **fields))
    return page, handles


@pytest.mark.parametrize('saved', (False, True))
@pytest.mark.parametrize('invalid', (False, True))
def test_reorder_replace_rejection_and_language_never_reassign_person(
    localized_server, saved, invalid,
):
    browser = Browser(localized_server)
    page, handles = reviewed_roster(browser, saved=saved)
    form = Forms(page).find('/matches/api/v1/create')
    choice = form['values']['perspective_seat']
    suffix = 'handle' if saved else 'name'
    fields = {f'forehand_{suffix}': handles.get('Bea', 'Bea'),
              f'middlehand_{suffix}': handles.get('Anna', 'Anna'), 'setup_action': 'update'}
    if invalid:
        fields['source_url'] = 'invalid-url'
    response = browser.submit(form, **fields)
    assert response[0] == (400 if invalid else 303)
    page = response[2].decode() if invalid else follow(browser, response)
    assert Forms(page).find('/matches/api/v1/create')['values']['perspective_seat'] == choice
    page = follow(browser, browser.submit(
        Forms(page).find('/actions/profile/language'), language='de'))
    current = Forms(page).find('/matches/api/v1/create')
    assert current['values']['perspective_seat'] == choice
    # A reviewed old Create must not overwrite a newer setup, even at the same generation.
    if not invalid:
        assert browser.submit(form, setup_action='create')[0] == 409
    page = follow(browser, browser.submit(current, forehand_mode='new', forehand_handle='',
        forehand_name='Dora', source_url='', setup_action='update'))
    current = Forms(page).find('/matches/api/v1/create')
    assert current['values']['perspective_seat'] == ''
    assert NativePage(page).field('perspective_seat')['type'] == 'hidden'
    assert 'name="setup_action" value="create"' not in page
    assert browser.submit(current, setup_action='create')[0] == 400
    assert localized_server.app_context.managed_stateful.active_match is None
    page = browser.page('/matches/new')
    page = follow(browser, browser.submit(
        Forms(page).find('/actions/profile/language'), language='en'))
    assert Forms(page).find('/matches/api/v1/create')['values']['perspective_seat'] == ''
    page = follow(browser, browser.submit(Forms(page).find('/matches/api/v1/create'),
        setup_action='choose_rearhand'))
    follow(browser, browser.submit(
        Forms(page).find('/matches/api/v1/create'), setup_action='create'))
    active = localized_server.app_context.managed_stateful.active_match
    definition = active.workspace.match_definition
    assert definition.perspective_player_id == next(p.player_id for p in definition.participants
                                                    if p.player_label == 'Clara')


def test_stale_reviewed_create_cannot_revert_same_generation_roster(localized_server):
    browser = Browser(localized_server)
    page, _ = reviewed_roster(browser)
    old = Forms(page).find('/matches/api/v1/create')
    page = follow(browser, browser.submit(old, forehand_name='Bea', middlehand_name='Anna',
                                         setup_action='update'))
    assert browser.submit(old, setup_action='create')[0] == 400
    assert localized_server.app_context.managed_stateful.active_match is None
    setup = localized_server.app_context.creation_setups['matches']
    assert dict(setup.values)['forehand_name'] == 'Bea'


def test_unsent_roster_language_return_keeps_person_until_update(localized_server):
    browser = Browser(localized_server)
    page, _ = reviewed_roster(browser)
    choice = Forms(page).find('/matches/api/v1/create')['values']['perspective_seat']
    pending = envelope(page, '/matches/api/v1/create', {
        'forehand_name': ['Bea'], 'middlehand_name': ['Anna']})
    page = follow(browser, enhanced_switch(browser, page, pending))
    form = Forms(page).find('/matches/api/v1/create')
    assert form['values']['forehand_name'] == 'Bea'
    assert form['values']['perspective_seat'] == choice
    page = follow(browser, browser.submit(form, setup_action='update'))
    assert Forms(page).find('/matches/api/v1/create')['values']['perspective_seat'] == choice
    follow(browser, browser.submit(
        Forms(page).find('/matches/api/v1/create'), setup_action='create'))
    active = localized_server.app_context.managed_stateful.active_match
    definition = active.workspace.match_definition
    assert definition.perspective_player_id == next(p.player_id for p in definition.participants
                                                    if p.player_label == 'Bea')


@pytest.mark.parametrize('clock_origin', (10.0, 10000.0))
def test_setup_review_does_not_generate_ids_or_write_and_expiry_stays_original(
    localized_server, monkeypatch, clock_origin,
):
    from types import SimpleNamespace

    import skatmind.app_web.player_seat_setup as seat_setup
    import skatmind.app_web.profile_driven_creation as creation

    clock = SimpleNamespace(now=clock_origin)
    # Only the setup clock is controlled; other HTTP/language clocks remain real.
    monkeypatch.setattr(seat_setup, 'time', SimpleNamespace(monotonic=lambda: clock.now))
    browser = Browser(localized_server)
    def forbidden(*_args, **_kwargs):
        pytest.fail('Setup attempted Product identity generation.')
    monkeypatch.setattr(creation, '_materialize_players', forbidden)
    monkeypatch.setattr(creation, 'generate_frontend_match_id_v1', forbidden)
    page = browser.page('/matches/new')
    context = localized_server.app_context
    setup = context.creation_setups['matches']
    assert setup.created_at == clock_origin
    old = Forms(page).find('/matches/api/v1/create')
    clock.now += 600
    page = follow(browser, browser.submit(old, match_title='No writes', forehand_name='Anna',
        middlehand_name='Bea', rearhand_name='Clara', setup_action='update'))
    clock.now += 600
    page = follow(browser, browser.submit(Forms(page).find('/matches/api/v1/create'),
        setup_action='choose_middlehand'))
    assert context.creation_setups['matches'].created_at == setup.created_at
    assert not context.frontend_profile.profile_path.exists()
    assert not tuple(context.managed_stateful.root('matches').iterdir())
    reviewed = context.creation_setups['matches']
    clock.now = setup.created_at + 1799
    page = browser.page('/matches/new')
    assert context.creation_setups['matches'] is reviewed
    assert 'name="setup_action" value="create"' in page
    clock.now += 1
    response = browser.submit(Forms(page).find('/matches/api/v1/create'), setup_action='create')
    assert response[0] == 409
    assert context.managed_stateful.active_match is None
    assert not context.frontend_profile.profile_path.exists()
    assert not tuple(context.managed_stateful.root('matches').iterdir())


@pytest.mark.parametrize('locale', ('de', 'en'))
@pytest.mark.parametrize('roster', ('saved', 'new', 'mixed'))
def test_native_person_review_then_create(localized_server, locale, roster):
    browser = Browser(localized_server)
    handles = saved_players(browser) if roster != 'new' else {}
    page = browser.page('/matches/new')
    page = follow(browser, browser.submit(Forms(page).find('/actions/profile/language'),
                                         language=locale))
    context = localized_server.app_context
    before = context.frontend_profile.profile_path.read_bytes()
    assert not re.search(r'<select[^>]*name="perspective_mode"', page)
    assert not re.search(r'<select[^>]*name="own_seat"', page)
    assert NativePage(page).field('perspective_seat')['type'] == 'hidden'
    fields = {'match_title': 'Named perspective', 'setup_action': 'choose_middlehand'}
    for seat, name in zip(('forehand', 'middlehand', 'rearhand'),
                          ('Anna', 'Bea', 'Clara'), strict=True):
        saved = roster == 'saved' or (roster == 'mixed' and name != 'Clara')
        fields[seat + '_mode'] = 'saved' if saved else 'new'
        fields[seat + ('_handle' if saved else '_name')] = handles[name] if saved else (
            'Dora' if roster == 'mixed' else name)
    response = browser.submit(Forms(page).find('/matches/api/v1/create'), **fields)
    assert response[0] == 303, response[2].decode()
    page = follow(browser, response)
    assert 'class="error-summary"' not in page
    form = Forms(page).find('/matches/api/v1/create')
    assert form['values']['perspective_seat'].startswith(('saved:', 'new:'))
    assert context.frontend_profile.profile_path.read_bytes() == before
    assert context.managed_stateful.active_match is None
    assert 'name="setup_action" value="create"' in page
    assert context.frontend_profile.profile_path.read_bytes() == before
    form = Forms(page).find('/matches/api/v1/create')
    follow(browser, browser.submit(form, setup_action='create'))
    active = context.managed_stateful.active_match
    definition = active.workspace.match_definition
    assert definition.perspective_player_id == next(p.player_id for p in definition.participants
                                                    if p.player_label == 'Bea')
    assert browser.submit(form, setup_action='create')[0] == 409


@pytest.mark.parametrize('locale', ('de', 'en'))
def test_literal_announcement_and_current_game_declarer_order(localized_server, locale):
    browser = Browser(localized_server)
    page = create_replay_match(browser, locale)
    active = localized_server.app_context.managed_stateful.active_match
    ids = {p.player_label: p.player_id for p in active.workspace.match_definition.participants}
    for position, names in ((1, ('Anna', 'Bea', 'Clara')), (2, ('Bea', 'Clara', 'Anna')),
                            (3, ('Clara', 'Anna', 'Bea'))):
        if position > 1:
            page = browser.page(f'/matches/position/{position}')
            page = follow(browser, browser.submit(operation_form(page, 'start_game')))
        native = NativePage(page)
        assert native.field('declarer_player_id')['options'] == ['', *(ids[n] for n in names)]
        assert native.field('declarer_player_id')['value'] == ''
        assert [c['name'] for c in native.controls if c.get('type') == 'checkbox'
                and c.get('name') in {'hand_game', 'ouvert', 'schneider_announced',
                                      'schwarz_announced'}] == [
                    'hand_game', 'schneider_announced', 'schwarz_announced', 'ouvert']
        # Selection survives rejected and accepted correction by identity, not ordinal.
        native.enter(declarer_player_id=ids['Bea'], game_type='grand', bid_value='-1')
        response = native.submit(browser, 'set_declaration')
        assert response[0] == 400
        rejected = NativePage(response[2].decode())
        assert rejected.field('declarer_player_id')['value'] == ids['Bea']
        rejected.enter(bid_value='18')
        page = follow(browser, rejected.submit(browser, 'set_declaration'))
        correction = NativePage(page)
        assert correction.field('declarer_player_id')['value'] == ids['Bea']
        assert correction.field('declarer_player_id')['options'] == ['', *(ids[n] for n in names)]
        assert [c['name'] for c in correction.controls if c.get('type') == 'checkbox'
                and c.get('name') in {'hand_game', 'ouvert', 'schneider_announced',
                                      'schwarz_announced'}] == [
                    'hand_game', 'schneider_announced', 'schwarz_announced', 'ouvert']


def test_all_normal_match_palettes_opt_in_without_recovery_or_progress_changes(localized_server):
    browser = Browser(localized_server)
    page = started(browser)
    native = NativePage(page)
    for field in ('evidence_perspective_hand', 'evidence_original_skat',
                  'evidence_discarded_cards'):
        from test_recording_task_focus import Hierarchy
        node = next(n for n in Hierarchy(page).nodes if n['attrs'].get('name') == field)
        assert any('data-balanced-grid' in parent['attrs'] for parent in node['parents'])
        assert native.owner(native.field(field)) is native.owner(native.field('game_type'))
    active = localized_server.app_context.managed_stateful.active_match
    anna = next(p.player_id for p in active.workspace.match_definition.participants
                if p.player_label == 'Anna')
    native.enter(declarer_player_id=anna, game_type='grand')
    page = follow(browser, native.submit(browser, 'set_declaration'))
    assert re.search(r'<fieldset\b[^>]*data-balanced-grid[^>]*data-card-mode="play"', page)
    assert 'recording-progress-layout' in page and 'data-recorded-summary' in page
    assert 'session-set-entry' not in page


@pytest.mark.parametrize('locale', ('de', 'en'))
def test_session_initial_and_correction_literal_announcement_order(localized_server, locale):
    from test_compact_declaration_web import before_declaration
    from test_session_declaration_correction_web import select

    browser = Browser(localized_server)
    page = browser.page('/sessions')
    follow(browser, browser.submit(Forms(page).find('/actions/profile/language'), language=locale))
    form = before_declaration(browser)
    for page in (browser.page(),):
        native = NativePage(page)
        flags = [c for c in native.controls if c.get('name') in {
            'hand_game', 'ouvert', 'schneider_announced', 'schwarz_announced'}]
        assert [c['name'] for c in flags] == [
            'hand_game', 'schneider_announced', 'schwarz_announced', 'ouvert']
        assert all('checked' not in c for c in flags)
        assert native.field('bid_value')['value'] == native.field('matadors')['value'] == ''
    follow(browser, browser.submit(form, game_type='grand', hand_game='true', bid_value='18'))
    page, _ = select(browser, 'set_declaration')
    native = NativePage(page)
    flags = [c for c in native.controls if c.get('name') in {
        'hand_game', 'ouvert', 'schneider_announced', 'schwarz_announced'}]
    assert [c['name'] for c in flags] == [
        'hand_game', 'schneider_announced', 'schwarz_announced', 'ouvert']
    assert ['checked' in c for c in flags] == [True, False, False, False]
    assert native.field('bid_value')['value'] == '18'
    assert native.field('matadors')['value'] == ''
