"""One native person action reviews the complete freshly entered Match roster."""

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_declaration_drafts import NativePage
from test_match_recording_recovery_web import follow
from test_match_setup_and_card_layout import saved_players
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

CREATE = '/matches/api/v1/create'
SEATS = ('forehand', 'middlehand', 'rearhand')


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def action_form(page, action):
    native = NativePage(page)
    buttons = [c for c in native.controls if c.get('name') == 'setup_action'
               and c.get('value') == action]
    assert buttons, f'Missing native submitter: {action}'
    owner = native.owner(buttons[0])
    assert owner['action'] == CREATE
    assert all(native.owner(c) is owner for c in native.controls
               if c.get('name') in {'match_title', 'perspective_seat', *(
                   seat + '_name' for seat in SEATS)})
    return {'action': CREATE, 'values': {
        **Forms(page).find(CREATE)['values'], 'setup_action': action}}


def fresh_roster(browser, roster='saved', locale='en'):
    handles = saved_players(browser) if roster != 'new' else {}
    page = browser.page('/matches/new')
    page = follow(browser, browser.submit(Forms(page).find('/actions/profile/language'),
                                         language=locale))
    values = {'match_title': 'Direct person review'}
    names = ('Anna', 'Bea', 'Dora' if roster == 'mixed' else 'Clara')
    for seat, name in zip(SEATS, names, strict=True):
        saved = roster == 'saved' or (roster == 'mixed' and name != 'Dora')
        values[seat + '_mode'] = 'saved' if saved else 'new'
        values[seat + ('_handle' if saved else '_name')] = handles[name] if saved else name
    return page, values, names


@pytest.mark.parametrize('locale', ('de', 'en'))
@pytest.mark.parametrize('roster', ('saved', 'new', 'mixed'))
@pytest.mark.parametrize('seat', SEATS)
def test_fresh_page_person_action_reviews_in_one_post(localized_server, locale, roster, seat):
    browser = Browser(localized_server)
    page, values, names = fresh_roster(browser, roster, locale)
    context = localized_server.app_context
    before = context.frontend_profile.profile_path.read_bytes()
    assert not any(c['tag'] == 'select' and c.get('name') == 'perspective_seat'
                   for c in NativePage(page).controls)
    nodes = Hierarchy(page).nodes
    for place in SEATS:
        button, = [n for n in nodes if n['tag'] == 'button'
                   and n['attrs'].get('value') == 'choose_' + place]
        assert any(p['attrs'].get('data-seat') == place for p in button['parents'])
    page = follow(browser, browser.submit(action_form(page, 'choose_' + seat), **values))
    setup = context.creation_setups['matches']
    assert setup.reviewed
    assert dict(setup.values)['perspective_seat'].startswith(('saved:', 'new:'))
    assert 'setup_action' not in dict(setup.values)
    assert names[SEATS.index(seat)] in page
    assert context.frontend_profile.profile_path.read_bytes() == before
    assert not tuple(context.managed_stateful.root('matches').iterdir())
    assert context.managed_stateful.active_match is None
    follow(browser, browser.submit(action_form(page, 'create')))
    definition = context.managed_stateful.active_match.workspace.match_definition
    assert definition.perspective_player_id == next(p.player_id for p in definition.participants
        if p.player_label == names[SEATS.index(seat)])


def test_implicit_enter_is_neutral_and_row_actions_are_the_only_person_editor(localized_server):
    browser = Browser(localized_server)
    page, values, _ = fresh_roster(browser)
    native = NativePage(page)
    submitters = [c for c in native.controls if c.get('name') == 'setup_action']
    assert submitters[0]['value'] == 'update'
    assert 'hidden' in submitters[0] and 'disabled' not in submitters[0]
    page = follow(browser, browser.submit(action_form(page, 'update'), **values))
    assert not localized_server.app_context.creation_setups['matches'].reviewed
    assert Forms(page).find(CREATE)['values']['perspective_seat'] == ''


@pytest.mark.parametrize('action', ('choose_left', 'choose_', 'choose_forehand_extra',
                                   ['choose_forehand', 'choose_rearhand'],
                                   ['update', 'choose_middlehand'], ['create', 'choose_forehand']))
def test_unsupported_or_ambiguous_action_never_reviews_or_writes(localized_server, action):
    browser = Browser(localized_server)
    page, values, _ = fresh_roster(browser)
    context = localized_server.app_context
    setup = context.creation_setups['matches']
    before = context.frontend_profile.profile_path.read_bytes()
    response = browser.submit(Forms(page).find(CREATE), **values, setup_action=action)
    assert response[0] == 400
    assert context.creation_setups['matches'] is setup
    assert context.frontend_profile.profile_path.read_bytes() == before
    assert not tuple(context.managed_stateful.root('matches').iterdir())


@pytest.mark.parametrize('bad,corrected', (
    ({'match_title': ''}, {'match_title': 'Corrected title'}),
    ({'source_url': 'not-a-url'}, {'source_url': ''}),
    ({'platform_choice': 'custom', 'custom_platform': ''}, {'custom_platform': 'Club'}),
    ({'local_date': '2026-03-29', 'local_time': '02:30', 'local_zone': 'Europe/Berlin'},
     {'local_date': '2026-03-30'}),
))
def test_person_and_values_survive_real_error_and_native_language_return(
    localized_server, bad, corrected,
):
    browser = Browser(localized_server)
    page, values, _ = fresh_roster(browser, 'new')
    context = localized_server.app_context
    before = context.frontend_profile.profile_path.read_bytes()
    response = browser.submit(action_form(page, 'choose_middlehand'), **{**values, **bad})
    assert response[0] == 400
    page = response[2].decode()
    form = Forms(page).find(CREATE)
    chosen = form['values']['perspective_seat']
    assert chosen.startswith('new:')
    assert form['values']['middlehand_name'] == 'Bea'
    assert not context.creation_setups['matches'].reviewed
    assert context.frontend_profile.profile_path.read_bytes() == before
    page = follow(browser, browser.submit(Forms(page).find('/actions/profile/language'),
                                         language='de'))
    form = Forms(page).find(CREATE)
    assert form['values']['perspective_seat'] == chosen
    for field, value in bad.items():
        assert form['values'][field] == value
    page = follow(browser, browser.submit(action_form(page, 'update'), **corrected))
    assert context.creation_setups['matches'].reviewed
    assert Forms(page).find(CREATE)['values']['perspective_seat'] == chosen
    assert context.managed_stateful.active_match is None
    follow(browser, browser.submit(action_form(page, 'create')))
    definition = context.managed_stateful.active_match.workspace.match_definition
    assert definition.perspective_player_id == next(p.player_id for p in definition.participants
                                                    if p.player_label == 'Bea')


def test_explicit_new_person_invalidates_old_create_and_does_not_save(localized_server):
    browser = Browser(localized_server)
    page, values, _ = fresh_roster(browser)
    page = follow(browser, browser.submit(action_form(page, 'choose_middlehand'), **values))
    old = action_form(page, 'create')
    chosen = old['values']['perspective_seat']
    page = follow(browser, browser.submit(action_form(page, 'choose_forehand'),
        forehand_handle=values['rearhand_handle'], rearhand_handle=values['forehand_handle']))
    current = action_form(page, 'create')
    assert current['values']['perspective_seat'] != chosen
    assert browser.submit(old)[0] == 400
    context = localized_server.app_context
    assert context.managed_stateful.active_match is None
    follow(browser, browser.submit(current))
    definition = context.managed_stateful.active_match.workspace.match_definition
    assert definition.perspective_player_id == next(p.player_id for p in definition.participants
                                                    if p.player_label == 'Clara')


@pytest.mark.parametrize('invalid', (
    'missing_other', 'missing_selected_name', 'unknown_selected', 'duplicate', 'mixed',
))
def test_person_action_validates_complete_roster_without_ids(
    localized_server, monkeypatch, invalid,
):
    import skatmind.app_web.profile_driven_creation as creation

    browser = Browser(localized_server)
    page, values, _ = fresh_roster(browser)
    if invalid == 'missing_other':
        values['rearhand_handle'] = ''
    elif invalid == 'missing_selected_name':
        values.update(middlehand_mode='new', middlehand_handle='', middlehand_name='')
    elif invalid == 'unknown_selected':
        values['middlehand_handle'] = 'f' * 64
    elif invalid == 'duplicate':
        values['forehand_handle'] = values['middlehand_handle']
    else:
        values['middlehand_name'] = 'Unrelated new name'
    def forbidden(*_args, **_kwargs):
        pytest.fail('Invalid choose-and-review attempted identity generation.')
    monkeypatch.setattr(creation, '_materialize_players', forbidden)
    monkeypatch.setattr(creation, 'generate_frontend_match_id_v1', forbidden)
    response = browser.submit(action_form(page, 'choose_middlehand'), **values)
    assert response[0] == 400
    if invalid == 'missing_selected_name':
        assert NativePage(response[2].decode()).field('middlehand_name')['aria-invalid'] == 'true'
    context = localized_server.app_context
    assert not context.creation_setups['matches'].reviewed
    assert not tuple(context.managed_stateful.root('matches').iterdir())


@pytest.mark.parametrize('field', ('setup_context', 'time_selection'))
def test_person_action_cannot_bypass_source_binding(localized_server, field):
    browser = Browser(localized_server)
    page, values, _ = fresh_roster(browser)
    context = localized_server.app_context
    setup = context.creation_setups['matches']
    response = browser.submit(action_form(page, 'choose_forehand'), **values, **{field: 'f' * 64})
    assert response[0] == 409
    assert context.creation_setups['matches'] is setup
    assert not tuple(context.managed_stateful.root('matches').iterdir())


def test_own_mode_and_hidden_language_values_cannot_be_bypassed(localized_server):
    browser = Browser(localized_server)
    handles = saved_players(browser)
    page = browser.page('/settings')
    follow(browser, browser.submit(Forms(page).find('/actions/profile/preferences'),
                                   own_player_handle=handles['Anna']))
    page = browser.page('/matches/new')
    context = localized_server.app_context
    before = context.frontend_profile.profile_path.read_bytes()
    response = browser.submit(action_form(page, 'choose_middlehand'), match_title='Own guarded',
        own_seat='rearhand', forehand_handle=handles['Bea'], middlehand_handle=handles['Clara'])
    assert response[0] == 400
    assert context.frontend_profile.profile_path.read_bytes() == before
    assert context.managed_stateful.active_match is None
    page = browser.page('/matches/new')
    raw = envelope(page, CREATE, {'perspective_seat': ['saved:' + handles['Clara']]})
    assert enhanced_switch(browser, page, raw)[0] == 400
    assert context.frontend_profile.profile_path.read_bytes() == before
    page = follow(browser, browser.submit(action_form(browser.page('/matches/new'), 'update'),
        match_title='Own guarded', own_seat='rearhand', forehand_handle=handles['Bea'],
        middlehand_handle=handles['Clara']))
    follow(browser, browser.submit(action_form(page, 'create')))
    definition = context.managed_stateful.active_match.workspace.match_definition
    assert definition.perspective_player_id == context.frontend_profile.document.own_player_id
