import json
import re

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import known_players, switch
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.language_form_preservation import (
    apply_language_page_values_v1,
    instrument_language_forms_v1,
    parse_language_page_values_v1,
)


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def envelope(page, action, values, *, index=0, disclosures=None):
    blocks = [match.group(0) for match in re.finditer(r'<form\b.*?</form>', page, re.S)
              if f'action="{action}"' in match.group(0)]
    identity = re.search(r'data-language-form="([0-9a-f]{64})"', blocks[index])[1]
    return json.dumps({"forms": [{"form": identity, "values": values}],
        "disclosures": ([False] * len(re.findall(r'<details\b', page))
                        if disclosures is None else disclosures)})


def enhanced_switch(browser, page, raw, locale="de"):
    return browser.submit(Forms(page).find("/actions/profile/language"),
                          language=locale, _frontend_language_values=raw)


def test_explicit_empty_false_repeated_values_and_exclusions():
    html = ('<details open><form action="/actions/analyze/run-guided">'
        '<input type="checkbox" name="hand_game" value="on" checked>'
        '<input type="checkbox" name="hand" value="CA">'
        '<input type="checkbox" name="hand" value="SA">'
        '<input name="bid_value" value="24"><input type="password" name="seed">'
        '<input type="file" name="request_file"><input type="hidden" name="revision" value="0">'
        '</form></details>')
    html, manifest = instrument_language_forms_v1(html)
    raw = envelope(html, "/actions/analyze/run-guided", {
        "hand_game": [], "hand": ["SA", "CA"], "bid_value": [""]})
    state = parse_language_page_values_v1(raw, manifest=manifest)
    rendered = apply_language_page_values_v1(html, state)
    assert '<details>' in rendered and '<details open' not in rendered
    assert 'value="on" checked' not in rendered
    assert 'value="CA" checked="checked"' in rendered
    assert 'value="SA" checked="checked"' in rendered
    assert 'name="bid_value" value=""' in rendered
    # Absence is not explicit clearing.
    absent = parse_language_page_values_v1(
        envelope(html, "/actions/analyze/run-guided", {}), manifest=manifest)
    assert 'value="on" checked' in apply_language_page_values_v1(html, absent)
    for name in ("seed", "request_file", "revision", "confirm_reset", "return_to", "language"):
        with pytest.raises(ValueError):
            parse_language_page_values_v1(
                envelope(html, "/actions/analyze/run-guided", {name: ["private"]}),
                manifest=manifest)


@pytest.mark.parametrize("raw", (
    pytest.param(" " * 262145, id="oversized"), '{"forms": [], "forms": []}',
    '{"forms": [], "disclosures": [0]}',
    '{"forms": [], "disclosures": [], "unknown": null}',
    '{"forms": {}, "disclosures": []}',
    '{"forms": [{"form": [], "values": {}}], "disclosures": []}',
))
def test_malformed_presentation_envelopes_fail_strictly(raw):
    _, manifest = instrument_language_forms_v1("")
    with pytest.raises(ValueError):
        parse_language_page_values_v1(raw, manifest=manifest)


def test_repeated_forms_use_stable_identity_and_regenerate_profile_generation(localized_server):
    browser = Browser(localized_server)
    known_players(browser)
    page = browser.page("/about")
    action = "/actions/profile/players/update"
    originals = [form["values"] for form in Forms(page).forms if form["action"] == action]
    raw = envelope(page, action, {"display_name": ["Unsent name"], "aliases": [""]}, index=1)
    page = follow(browser, enhanced_switch(browser, page, raw))
    returned = [form["values"] for form in Forms(page).forms if form["action"] == action]
    assert returned[0]["display_name"] == originals[0]["display_name"]
    assert returned[1]["display_name"] == "Unsent name"
    assert returned[2]["display_name"] == originals[2]["display_name"]
    profile = localized_server.app_context.frontend_profile
    assert returned[1]["profile_generation"] == str(profile.generation)
    assert "Unsent name" not in str(profile.document.known_players)
    assert localized_server.app_context.language_context.pending is None
    form = [form for form in Forms(page).forms if form["action"] == action][1]
    follow(browser, browser.submit(form, aliases="", platform_player_ids=""))
    assert "Unsent name" in str(
        localized_server.app_context.frontend_profile.document.known_players)


def test_product_error_survives_malformed_language_with_early_safe_origin(localized_server):
    browser = Browser(localized_server)
    page = browser.page("/sessions")
    _, _, body = browser.submit(
        Forms(page).find("/sessions/create"), game_name="Safe submitted name")
    page = body.decode()
    original = localized_server.app_context.form_feedback._feedback["sessions"]
    status, _, body = enhanced_switch(browser, page, '{"forms": [], "forms": []}')
    assert status == 400
    page = body.decode()
    assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == "/sessions"
    assert Forms(page).find("/sessions/create")["values"]["game_name"] == "Safe submitted name"
    assert localized_server.app_context.form_feedback._feedback["sessions"] is original
    assert '<html lang="en">' in page and 'value="en" lang="en" aria-pressed="true"' in page
    assert 'name="language" value="de" lang="de" aria-pressed="false"' in page
    page = switch(browser, page, "de")
    assert "Safe submitted name" in page


def test_disclosures_required_by_validation_cannot_be_closed_and_select_can_be_cleared():
    html = ('<details open><details><form action="/sessions/command">'
        '<input type="hidden" name="kind" value="record_dealt_card">'
        '<select name="card" aria-invalid="true"><option value="CA" selected>CA</option>'
        '<option value="SA">SA</option></select></form></details></details>')
    html, manifest = instrument_language_forms_v1(html)
    raw = envelope(html, "/sessions/command", {"card": []})
    restored = apply_language_page_values_v1(
        html, parse_language_page_values_v1(raw, manifest=manifest))
    assert restored.count('<details open="open">') == 2
    assert '<option value="" selected></option>' in restored
    assert '<option value="CA" selected>' not in restored


@pytest.mark.parametrize("values", (
    pytest.param({"game_name": ["x" * 8193]}, id="oversized-field"),
    {"game_name": ["first", "second"]},
    {"game_name": True}, {"game_name": [None]}, {"capture_mode": ["foreign"]},
    {"player_1_handle": ["../foreign"]}, {"player_1_handle": ["0" * 64]},
    {"profile_generation": ["1"]}, {"return_to": ["//external.invalid"]},
))
def test_envelope_values_reject_before_profile_save(localized_server, values):
    browser = Browser(localized_server)
    page = browser.page("/sessions")
    profile = localized_server.app_context.frontend_profile
    raw = envelope(page, "/sessions/create", values)
    status, _, body = enhanced_switch(browser, page, raw)
    assert status == 400
    assert localized_server.app_context.frontend_profile is profile
    returned = Forms(body.decode()).find("/actions/profile/language")
    assert returned["values"]["return_to"] == "/sessions"


def test_page_bindings_are_bounded_and_evicted_bindings_cannot_save(localized_server):
    browser = Browser(localized_server)
    form = Forms(browser.page("/about")).find("/actions/profile/language")
    for _ in range(33):
        browser.page("/about")
    assert len(localized_server.app_context.language_context.pages) == 32
    assert browser.submit(form, language="de")[0] == 409
    assert localized_server.app_context.frontend_profile.document is None
