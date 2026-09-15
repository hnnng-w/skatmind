"""Fixed recording scope over real friendly creation and existing metadata actions."""

import json
import re
from html import escape, unescape
from unittest.mock import patch

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_local_time_entry_web import local_form
from test_match_recording_recovery_web import follow, operation_form, start_match
from test_profile_driven_match_creation import _entropy_source, _values
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.friendly_creation_rendering import render_profile_driven_match_creation_v1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.profile_driven_creation import prepare_profile_driven_match_creation_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.capture_web.operations import _creation_definition
from skatmind.match_tournament_format import EUROSKAT_36_STANDARD_V1_FORMAT as FORMAT
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1 as rotation

PLATFORMS = (
    ("euroskat", "EuroSkat"), ("in_person", "In-person game"),
    ("other_online", "Other online platform"), ("unknown", "Unknown"),
    ("custom", 'Club <18> & "Zocker"'),
)
CREATE = "/matches/api/v1/create"
SEATS = ("forehand", "middlehand", "rearhand")


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def assert_scope(page, locale, *, creation=True):
    assert page.count('class="match-recording-format"') == 1
    assert text(locale, "creation.match.format") in page
    assert text(locale, "creation.match.format_value", games=36, players=3) in page
    assert text(locale, "creation.match.format_help") in page
    assert not re.search(
        r'<(?:input|select|textarea)[^>]*name="(?:format|format_id|tournament_format)"', page)
    if creation:
        technical = re.search(
            r'<details class="technical-details"[^>]*>.*?<pre lang="en">(.*?)</pre>',
            page, re.S)
        assert json.loads(unescape(technical[1])) == FORMAT.to_dict()
        assert "euroskat_36_standard_v1" not in page[:technical.start()]
        assert "format_id" not in Forms(page).find(CREATE)["values"]


def assert_workspace(workspace, platform, *, names=("Anna", "Peter", "Mira"),
                     perspective="middlehand"):
    definition = workspace.match_definition
    assert definition.tournament_format is FORMAT
    assert definition.game_platform == platform
    assert len(workspace.slots) == 36
    ids = {p.player_label: p.player_id for p in definition.participants}
    first = rotation(definition, 1)
    assert tuple(getattr(first, f"{seat}_player_id") for seat in SEATS) == tuple(
        ids[name] for name in names)
    assert definition.perspective_player_id == getattr(first, f"{perspective}_player_id")
    for position, slot in enumerate(workspace.slots, 1):
        assert slot.match_position == position
        assignment = rotation(definition, position)
        assert {getattr(assignment, f"{seat}_player_id") for seat in SEATS} == set(ids.values())


@pytest.mark.parametrize("choice,platform", PLATFORMS)
@pytest.mark.parametrize("save", (False, True))
@pytest.mark.parametrize("url,kind", (("", "manual_observation"),
    ("https://youtu.be/synthetic", "youtube_video")))
def test_platform_changes_only_descriptive_metadata_in_fixed_workspace(choice, platform, save,
                                                                      url, kind):
    profile = build_local_frontend_profile_v1(preferred_game_platform="Other online platform")
    common = _values(source_url=url, played_at="2026-09-03T19:30:00+02:00",
        forehand_platform_id="exact=anna", save_platform="on" if save else "")
    def prepare(selection):
        return prepare_profile_driven_match_creation_v1(
            {**common, "platform_choice": selection, "custom_platform": PLATFORMS[-1][1]},
            profile=profile, expected_profile_generation=7, existing_match_ids=(),
            entropy_source=_entropy_source())
    prepared, baseline = prepare(choice), prepare("euroskat")
    assert dict(prepared.product_values) == {**baseline.product_values, "game_platform": platform}
    assert prepared.expected_profile_generation == 7
    assert prepared.profile_document.preferred_game_platform == (
        platform if save else profile.preferred_game_platform)
    workspace = create_match_workspace_v1(_creation_definition(prepared.product_values))
    assert_workspace(workspace, platform)
    definition = workspace.match_definition
    assert definition.source.source_kind == kind
    assert definition.source.source_url == (url or None)
    assert definition.played_at == "2026-09-03T19:30:00+02:00"
    assert next(p.platform_player_id for p in definition.participants
                if p.player_label == "Anna") == "exact=anna"
    other = _creation_definition(baseline.product_values)
    for position in range(1, 37):
        assert rotation(definition, position) == rotation(other, position)


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("choice,platform", (("unknown", None), *PLATFORMS))
def test_saved_platform_selection_and_escaped_custom_text_keep_one_readonly_scope(
    locale, choice, platform,
):
    page = render_profile_driven_match_creation_v1(
        profile=build_local_frontend_profile_v1(preferred_game_platform=platform),
        profile_generation=7, locale=locale)
    assert_scope(page, locale)
    values = Forms(page).find(CREATE)["values"]
    assert values["platform_choice"] == choice
    assert "save_platform" not in values and "save_players" not in values
    assert values["custom_platform"] == (platform if choice == "custom" else "")
    if choice == "custom":
        assert escape(platform, quote=True) in page and platform not in page


@pytest.mark.parametrize("locale", ("de", "en"))
def test_returned_forms_error_setup_correction_create_and_strict_reopen(localized_server, locale):
    import skatmind.app_web.server as server_module

    browser = Browser(localized_server)
    app = localized_server.app_context
    page = switch(browser, browser.page("/matches/new"), locale)
    for choice, platform, save in (("euroskat", "EuroSkat", True),
                                   ("custom", PLATFORMS[-1][1], False)):
        page = browser.page("/matches/new")
        assert_scope(page, locale)
        profile_before = app.frontend_profile.profile_path.read_bytes()
        active_before = app.managed_stateful.active_match
        root = app.managed_stateful.root("matches")
        files_before = {p: p.read_bytes() for p in root.glob("*.json")}
        with patch.object(server_module, "create_unified_match_v1",
                          wraps=server_module.create_unified_match_v1) as creates:
            response = browser.submit(Forms(page).find(CREATE), match_title="Fixed scope",
                forehand_name="Anna", middlehand_name="anna", rearhand_name="Mira",
                perspective_seat="middlehand", platform_choice=choice,
                custom_platform=PLATFORMS[-1][1], source_url="https://youtu.be/synthetic",
                played_date="2026-09-03", local_date="2026-09-03", local_time="19:30",
                forehand_platform_id="exact=anna", save_platform="on" if save else "",
                setup_action="update")
            assert response[0] == 400
            assert app.frontend_profile.profile_path.read_bytes() == profile_before
            assert app.managed_stateful.active_match is active_before
            page = response[2].decode()
            assert_scope(page, locale)
            other = "en" if locale == "de" else "de"
            for language in (other, locale):
                page = switch(browser, page, language)
                assert_scope(page, language)
                values = Forms(page).find(CREATE)["values"]
                assert values["platform_choice"] == choice
                assert values["custom_platform"] == PLATFORMS[-1][1]
                assert values["source_url"] == "https://youtu.be/synthetic"
                assert values["local_time"] == "19:30" and values["middlehand_name"] == "anna"
            profile_before = app.frontend_profile.profile_path.read_bytes()
            page = follow(browser, browser.submit(Forms(page).find(CREATE),
                middlehand_name="Peter", setup_action="update"))
            assert_scope(page, locale)
            assert app.frontend_profile.profile_path.read_bytes() == profile_before
            assert app.managed_stateful.active_match is active_before
            assert {p: p.read_bytes() for p in root.glob("*.json")} == files_before
            creates.assert_not_called()
            page = follow(browser, browser.submit(Forms(page).find(CREATE), setup_action="create"))
            assert creates.call_count == 1
        active = app.managed_stateful.active_match
        accepted = load_match_workspace_file_v1(active.path).document.workspace
        assert_workspace(accepted, platform)
        assert accepted.revision == 0
        assert accepted.match_definition.match_id.startswith("frontend-match-")
        assert accepted.match_definition.source.source_kind == "youtube_video"
        assert accepted.match_definition.played_at == "2026-09-03T19:30:00+02:00"
        assert app.frontend_profile.document.preferred_game_platform == "EuroSkat"
        assert_scope(page, locale, creation=False)
        before = active.path.read_bytes()
        reopen = next(f for f in Forms(browser.page("/matches")).forms
            if f["action"] == "/matches/open" and f["values"]["handle"] == active.handle)
        follow(browser, browser.submit(reopen))
        assert app.managed_stateful.active_match.path.read_bytes() == before
        assert load_match_workspace_file_v1(active.path).document.workspace == accepted


def test_metadata_platform_edit_preserves_play_prefix_noop_stale_and_passive_contracts(
    localized_server,
):
    browser = Browser(localized_server)
    page = start_match(browser)
    declarer = re.search(r'<option value="([^"]+)"[^>]*>Alexandra Long-Synthetic-Player-Name',
                         page)[1]
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=declarer, game_type="grand", hand_game="true"))
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
        card_evidence_mode="exact", cards="SA CA C10 CK CQ C9 C8 C7 H10 H9".split()))
    for card in ("SA", "S9", "S7"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    page = browser.page("/matches/review/1")
    response = browser.submit(operation_form(page, "analyze_decision"),
        recommendation_method="immediate_expected_value", immediate_sample_count="1")
    assert response[0] == 303, re.sub(r"<[^>]+>", " ", response[2].decode())
    page = follow(browser, response)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    original = active.workspace
    before = active.path.read_bytes()
    profile_before = app.frontend_profile.profile_path.read_bytes()
    reports = active.capture.report_store
    reports_generation = reports.generation
    report = reports.list()[0]
    assert report.value.status == "executed"
    report_url = f"/matches/api/v1/reports/{report.report_id}.json"
    report_bytes = browser.request("GET", report_url)[2]
    with patch("skatmind.capture_web.analysis.execute_match_decision_analysis_v1",
               side_effect=AssertionError("Unexpected analysis")):
        page = browser.page("/matches/position/1")
        assert app.frontend_profile.profile_path.read_bytes() == profile_before
        page = switch(browser, page, "de")
        assert active.path.read_bytes() == before and reports.generation == reports_generation
        assert_scope(page, "de", creation=False)
        page = follow(browser, browser.submit(local_form(page, "match-metadata")))
        assert active.path.read_bytes() == before and reports.generation == reports_generation
        assert reports.list() == (report,)
        assert browser.request("GET", report_url)[2] == report_bytes
        stale = local_form(page, "match-metadata")
        response = browser.submit(stale, game_platform="", title="Rejected title")
        assert response[0] == 400 and active.workspace is original
        page = response[2].decode()
        assert local_form(page, "match-metadata")["values"]["game_platform"] == ""
        assert active.workspace.match_definition.game_platform == "In-person game"
        profile_before = app.frontend_profile.profile_path.read_bytes()
        page = follow(browser, browser.submit(local_form(page, "match-metadata"),
            game_platform=PLATFORMS[-1][1], title=original.match_definition.title))
        assert active.workspace.revision == original.revision + 1
        assert reports.generation == reports_generation + 1
        assert reports.list() == ()
        assert active.workspace.slots == original.slots
        assert active.workspace.match_definition.to_dict() == {
            **original.match_definition.to_dict(), "game_platform": PLATFORMS[-1][1]}
        assert active.workspace.match_definition.tournament_format is FORMAT
        assert app.frontend_profile.profile_path.read_bytes() == profile_before
        before = active.path.read_bytes()
        assert browser.submit(stale, game_platform="EuroSkat")[0] == 409
        assert active.path.read_bytes() == before
        follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
        assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
