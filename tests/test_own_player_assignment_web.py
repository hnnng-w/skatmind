"""Real creation and separate rejection/fault probes for the R02 own assignment."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from html.parser import HTMLParser

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms
from test_settings_seat_setup_web import add_players, player_action, setup_own

from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def creation(family):
    return (("/sessions", "/sessions/create", "game_name") if family == "sessions" else
            ("/matches/new", "/matches/api/v1/create", "match_title"))


class Controls(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.controls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"input", "select", "textarea", "button"} and "name" in attrs:
            self.controls.append((tag, attrs))


def assert_creation_controls(page, action):
    start = page.index(f'<form method="post" action="{action}"')
    html = page[start:page.index("</form>", start)]
    controls = Controls(html).controls
    fields = Counter(a["name"] for tag, a in controls
                     if tag != "button" and a.get("type") != "radio")
    assert set(fields.values()) == {1}, fields
    assert all("disabled" not in a for _, a in controls)
    for seat in ("forehand", "middlehand", "rearhand"):
        assert next(tag for tag, a in controls if a["name"] == seat + "_handle") == "select"
    assert 'class="roster-summary"' not in html
    return html


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_real_collision_language_correction_and_manual_c_perspective(localized_server, family):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    context = localized_server.app_context
    original = context.frontend_profile.document
    route, action, title = creation(family)
    page = browser.page(route)
    assert_creation_controls(page, action)
    metadata = ({} if family == "sessions" else {
        "platform_choice": "custom", "custom_platform": 'Club <18> & "Friends"',
        "local_date": "2026-09-03", "local_time": "19:30", "local_zone": "Europe/Berlin",
        "played_date": "2026-09-03", "source_url": "https://youtu.be/synthetic",
        "source_title": "Exact source", "source_channel_name": "Synthetic channel",
        "match_timecode_start": "01:02:03", "forehand_platform_id": "B-account",
        "middlehand_platform_id": "C-account", "rearhand_platform_id": "entered-B-account"})
    response = browser.submit(Forms(page).find(action), **{title: "Retained collision",
        "own_seat": "rearhand", "forehand_handle": handles[1],
        "middlehand_handle": handles[2], "rearhand_handle": handles[1],
        "setup_action": "update", **metadata})
    assert response[0] == 400
    page = response[2].decode()
    assert context.frontend_profile.document is original
    for locale in ("de", "en"):
        page = switch(browser, page, locale)
        block = assert_creation_controls(page, action)
        values = Forms(page).find(action)["values"]
        assert values["rearhand_handle"] == handles[1]
        assert all(values[key] == value for key, value in metadata.items())
        assert 'name="rearhand_handle" aria-invalid="true"' in block
        assert text(locale, "validation.message.setup_occupied") in page
        assert (context.managed_stateful.active_session
                is context.managed_stateful.active_match is None)
    # Explicitly select A (not a placeholder workaround); manual perspective remains C.
    page = follow(browser, browser.submit(Forms(page).find(action),
        perspective_mode="manual", perspective_seat="middlehand", rearhand_handle=handles[0],
        setup_action="update", **({"rearhand_platform_id": "A-account"} if metadata else {})))
    assert_creation_controls(page, action)
    follow(browser, browser.submit(Forms(page).find(action), setup_action="create"))
    assert context.frontend_profile.document.own_player_id == original.own_player_id
    assert context.frontend_profile.document.preferred_perspective_player_id == (
        original.preferred_perspective_player_id)
    c = original.known_players[2].player_id
    if family == "sessions":
        state = context.managed_stateful.active_session.state
        assert tuple(p.player_label for p in state.players) == ("B", "C", "A")
        assert state.local_player_id == c and state.revision == 0
    else:
        workspace = context.managed_stateful.active_match.workspace
        definition = workspace.match_definition
        assert workspace.revision == 0 and definition.perspective_player_id == c
        assert definition.played_at == "2026-09-03T19:30:00+02:00"
        assert definition.game_platform == metadata["custom_platform"]
        assert {p.player_label: p.platform_player_id for p in definition.participants} == {
            "A": "A-account", "B": "B-account", "C": "C-account"}


def test_account_move_conflict_retains_both_values_through_language(localized_server):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    action = "/matches/api/v1/create"
    page = follow(browser, browser.submit(Forms(browser.page("/matches/new")).find(action),
        own_seat="rearhand", rearhand_handle=handles[0], rearhand_platform_id="source-account",
        setup_action="update"))
    response = browser.submit(Forms(page).find(action), own_seat="forehand",
        forehand_handle=handles[0], forehand_platform_id="target-account", setup_action="update")
    assert response[0] == 400
    page = switch(browser, response[2].decode(), "de")
    assert 'class="advanced-settings" open' in page
    values = Forms(page).find(action)["values"]
    assert values["rearhand_platform_id"] == "source-account"
    assert values["forehand_platform_id"] == "target-account"
    assert values["own_seat"] == "forehand"
    assert text("de", "validation.message.setup_account_conflict") in page
    page = follow(browser, browser.submit(Forms(page).find(action),
        rearhand_platform_id="", setup_action="update"))
    values = Forms(page).find(action)["values"]
    assert values["forehand_platform_id"] == "target-account"
    assert values["rearhand_platform_id"] == values["rearhand_handle"] == ""


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_manual_to_own_pending_perspective_error_keeps_resolution_control(localized_server, family):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    route, action, title = creation(family)
    response = browser.submit(Forms(browser.page(route)).find(action), **{
        title: "Pending perspective", "perspective_mode": "own", "own_seat": "rearhand",
        "perspective_seat": "middlehand", "forehand_handle": handles[1],
        "middlehand_handle": handles[2], "setup_action": "update"})
    assert response[0] == 400
    page = switch(browser, response[2].decode(), "de")
    assert '<select name="perspective_seat" aria-invalid="true"' in page
    assert text("de", "validation.message.setup_own_binding") in page
    page = follow(browser, browser.submit(Forms(page).find(action),
        perspective_seat="rearhand", setup_action="update"))
    assert Forms(page).find(action)["values"]["perspective_seat"] == "rearhand"


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_changed_final_create_is_not_repaired_into_review(localized_server, family):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    page, action = setup_own(browser, family, handles, "rearhand")
    assert_creation_controls(page, action)
    form = Forms(page).find(action)
    # Replacing A by blank would project back to A, but Create must compare first.
    response = browser.submit(form, rearhand_handle="", setup_action="create")
    assert response[0] == 400
    assert text("en", "validation.message.setup_review_required") in response[2].decode()
    page = follow(browser, browser.submit(Forms(response[2].decode()).find(action),
        rearhand_handle=handles[0], setup_action="update"))
    follow(browser, browser.submit(Forms(page).find(action), setup_action="create"))
    context = localized_server.app_context
    assert len(tuple(context.managed_stateful.root(family).glob("*.json"))) == 1
    assert browser.submit(form, setup_action="create")[0] == 409


@pytest.mark.parametrize("family", ("sessions", "matches"))
@pytest.mark.parametrize("change", ("expired", "superseded", "own_changed", "removed", "forged"))
def test_stale_own_setup_never_rebinds_or_creates(localized_server, family, change):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    page, action = setup_own(browser, family, handles, "rearhand")
    context = localized_server.app_context
    form = Forms(page).find(action)
    setup = context.creation_setups[family]
    if change == "expired":
        context.creation_setups[family] = replace(setup, created_at=setup.created_at - 1801)
    elif change == "superseded":
        context.creation_setups.pop(family)
        browser.page(creation(family)[0])
    elif change == "own_changed":
        follow(browser, browser.submit(Forms(browser.page("/settings")).find(
            "/actions/profile/preferences"), own_player_handle=handles[2]))
    elif change == "removed":
        page = follow(browser, browser.submit(player_action(browser.page("/settings"),
            "remove-preview", handles[0])))
        follow(browser, browser.submit(player_action(page, "remove", handles[0]),
                                        confirm_replace="on"))
    else:
        form["values"]["own_player_handle"] = handles[1]
    before = context.frontend_profile.profile_path.read_bytes()
    assert browser.submit(form, setup_action="update" if change == "forged" else "create")[0] == 409
    assert context.frontend_profile.profile_path.read_bytes() == before
    assert not tuple(context.managed_stateful.root(family).glob("*.json"))


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_competing_final_submissions_create_only_once(localized_server, family):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    page, action = setup_own(browser, family, handles, "rearhand")
    form = Forms(page).find(action)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: browser.submit(form, setup_action="create"), range(2)))
    assert sorted(response[0] for response in responses) == [303, 409]
    root = localized_server.app_context.managed_stateful.root(family)
    assert len(tuple(root.glob("*.json"))) == 1


@pytest.mark.parametrize("family", ("sessions", "matches"))
@pytest.mark.parametrize("failure", ("product", "profile"))
def test_one_use_creation_failure_has_no_retry_or_rollback(localized_server, monkeypatch,
                                                         family, failure):
    import skatmind.app_web.server as server_module

    browser = Browser(localized_server)
    _, handles = add_players(browser)
    page, action = setup_own(browser, family, handles, "rearhand")
    form = Forms(page).find(action)
    context = localized_server.app_context
    before = context.frontend_profile.profile_path.read_bytes()
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise OSError("Synthetic storage failure")
    if failure == "profile":
        monkeypatch.setattr(server_module, "save_prepared_frontend_profile_v1", fail)
    else:
        monkeypatch.setattr(server_module, "create_guided_session_v1" if family == "sessions"
                            else "create_unified_match_v1", fail)
    response = browser.submit(form, setup_action="create")
    assert response[0] == (303 if failure == "profile" else 500)
    if failure == "profile":
        assert text("en", "creation.profile_storage_warning") in follow(browser, response)
    count = len(tuple(context.managed_stateful.root(family).glob("*.json")))
    assert count == (1 if failure == "profile" else 0)
    assert browser.submit(form, setup_action="create")[0] == 409
    assert calls == [1] and context.frontend_profile.profile_path.read_bytes() == before


def test_setup_and_rejection_retain_real_results_without_ids_saves_or_execution(
    localized_server, monkeypatch,
):
    from test_match_recording_recovery_web import operation_form
    from test_recorded_decision_context_web import record_context_match
    from test_session_recorded_review_web import record_live_game, review_first

    import skatmind.app_web.server as server_module

    browser = Browser(localized_server)
    record_live_game(browser, play_count=3)
    review_first(browser)
    record_context_match(browser)
    follow(browser, browser.submit(operation_form(browser.page("/matches/review/1"),
                                                   "analyze_decision")))
    context = localized_server.app_context
    session = context.managed_stateful.active_session
    match = context.managed_stateful.active_match
    execution = session.execution
    reports = match.capture.report_store.list()
    assert execution is not None and len(reports) == 1
    _, handles = add_players(browser)
    files = {p: p.read_bytes() for p in (session.path, match.path,
                                       context.frontend_profile.profile_path)}
    def forbidden(*args, **kwargs):
        pytest.fail("Setup or rejection generated an ID, saved, collected, or executed")
    with monkeypatch.context() as guard:
        guard.setattr(server_module.secrets, "token_bytes", forbidden)
        guard.setattr(server_module, "save_prepared_frontend_profile_v1", forbidden)
        guard.setattr(server_module, "create_guided_session_v1", forbidden)
        guard.setattr(server_module, "create_unified_match_v1", forbidden)
        guard.setattr("skatmind.app_web.execution.execute", forbidden)
        guard.setattr("skatmind.session_checkpoint_collection.collect_session_decision_checkpoint_v1",
                      forbidden)
        for family in ("sessions", "matches"):
            page, action = setup_own(browser, family, handles, "rearhand")
            response = browser.submit(Forms(page).find(action), own_seat="forehand",
                forehand_handle=handles[1], setup_action="update")
            assert response[0] == 400
            assert session.execution is execution and match.capture.report_store.list() == reports
            assert all(path.read_bytes() == value for path, value in files.items())
    # Successful same-family activation still uses the existing invalidation boundary.
    for family in ("sessions", "matches"):
        route, action, _ = creation(family)
        page = follow(browser, browser.submit(Forms(browser.page(route)).find(action),
                                               own_seat="rearhand", setup_action="update"))
        follow(browser, browser.submit(Forms(page).find(action), setup_action="create"))
        if family == "sessions":
            assert context.managed_stateful.active_session is not session
            assert context.managed_stateful.active_session.execution is None
            assert match.capture.report_store.list() == reports
        else:
            assert context.managed_stateful.active_match is not match
            assert not context.managed_stateful.active_match.capture.report_store.list()
