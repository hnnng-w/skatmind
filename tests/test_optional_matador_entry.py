"""R07a/b: literal local help and unchanged genuine declaration/correction forms."""

import pytest
from test_compact_declaration_web import before_declaration, declaration_form
from test_frontend_language_switching import localized_server as _localized_server
from test_match_card_correction_ui import activated_form
from test_match_recording_recovery_web import follow, start_match
from test_recording_task_focus import Hierarchy
from test_session_declaration_correction_web import PREFIX, select
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.task_first_rendering import input_field

HELP = {
    "en": (
        "Unknown? Leave blank. Suit: 1–11; Grand: 1–4; Null: leave blank. "
        "Count consecutive top trumps, held or missing, from the Jack of Clubs. "
        "With 2 or without 2: enter 2.",
        "The count must be verifiable from this Session's permitted evidence; "
        "Live defenders must leave it blank.",
        "Matadors (optional)",
    ),
    "de": (
        "Unbekannt? Leer lassen. Farbspiel: 1–11; Grand: 1–4; Null: leer lassen. "
        "Lückenlos höchste vorhandene oder fehlende Trümpfe ab dem Kreuz-Buben zählen. "
        "Mit 2 oder ohne 2: 2 eingeben.",
        "Die Zahl muss anhand der zulässigen Informationen dieser Session überprüfbar sein; "
        "Live-Gegenspieler müssen sie leer lassen.",
        "Spitzenzahl (optional)",
    ),
}


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def assert_count(page, locale, *, session, value="", error=False):
    markup = Hierarchy(page)
    controls = [n for n in markup.nodes if n["attrs"].get("name") == "matadors"]
    control, = controls
    attrs = control["attrs"]
    assert control["tag"] == "input" and attrs["type"] == "text"
    assert attrs["value"] == value and attrs["class"] == "declaration-matadors"
    restrictions = {"required", "min", "max", "step", "pattern", "maxlength", "inputmode"}
    assert not restrictions & attrs.keys()
    label, = [n for n in control["parents"] if n["tag"] == "label"]
    assert label["text"].strip() == HELP[locale][2]
    ids = [n["attrs"]["id"] for n in markup.nodes if "id" in n["attrs"]]
    assert len(ids) == len(set(ids))
    associated = [markup.by_id(identity) for identity in attrs["aria-describedby"].split()]
    help_nodes = [n for n in associated if n["attrs"].get("class") != "field-error"]
    assert [n["text"] for n in help_nodes] == list(HELP[locale][:2 if session else 1])
    details, = [n for n in control["parents"] if n["attrs"].get("class") == "declaration-count"]
    local = [n for n in markup.nodes if any(p is details for p in n["parents"])]
    assert not any(n["tag"] == "details" for n in local)
    for sentence in HELP[locale][:2 if session else 1]:
        assert details["text"].count(sentence) == 1
    if value or error:
        assert "open" in details["attrs"]
    if error:
        assert attrs["aria-invalid"] == "true"
        assert any(n["attrs"].get("class") == "field-error" for n in associated)
        assert f'href="#{attrs["id"]}"' in page
    bid, = [n["attrs"] for n in markup.nodes if n["attrs"].get("name") == "bid_value"]
    assert bid == {"name": "bid_value", "type": "text", "value": bid["value"]}
    return attrs


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("family", ("session", "match"))
def test_returned_entry_has_one_opt_in_count_and_literal_help(localized_server, locale, family):
    browser = Browser(localized_server)
    if family == "session":
        before_declaration(browser)
        page = browser.page()
    else:
        page = start_match(browser)
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    assert_count(page, locale, session=family == "session")
    assert input_field("en", "sample_count", "task.field.sample_count", 100, kind="number") == (
        '<label>Samples <input name="sample_count" type="number" value="100"></label>')


@pytest.mark.parametrize("family", ("session", "match"))
def test_safe_invalid_text_and_help_errors_survive_native_language(localized_server, family):
    browser = Browser(localized_server)
    if family == "session":
        form = before_declaration(browser)
        active = localized_server.app_context.managed_stateful.active_session
    else:
        form = declaration_form(start_match(browser), "match-declaration")
        active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    response = browser.submit(form, game_type="grand", matadors="12345bad")
    assert response[0] == 400  # Deliberate HTTP input; native editing is separate evidence.
    page = response[2].decode()
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert_count(page, locale, session=family == "session", value="12345bad", error=True)
        assert active.path.read_bytes() == before


def test_known_count_staged_editor_cancel_noop_clear_apply_and_reopen(localized_server):
    browser = Browser(localized_server)
    entry = before_declaration(browser, defender=False,
        hand="CJ SJ HJ DJ CA C10 CK CQ C9 C8".split())
    follow(browser, browser.submit(entry, game_type="grand", hand_game="true", matadors="4"))
    active = localized_server.app_context.managed_stateful.active_session
    before, checkpoints = active.path.read_bytes(), active.decision_checkpoints
    page, form = select(browser, "set_declaration")
    assert_count(page, "en", session=True, value="4")
    selection = active.declaration_correction.selected
    page = follow(browser, browser.submit(form, matadors=""))
    assert 'class="declaration-matadors"' not in page
    assert active.path.read_bytes() == before and active.decision_checkpoints is checkpoints
    assert active.declaration_correction.selected is selection
    follow(browser, browser.submit(Forms(page).find(PREFIX + "cancel")))
    page, form = select(browser, "set_declaration")
    page = follow(browser, browser.submit(form))
    assert active.declaration_correction.preview.result.status == "unchanged"
    follow(browser, browser.submit(activated_form(page, PREFIX + "apply")))
    assert active.path.read_bytes() == before
    page, form = select(browser, "set_declaration")
    page = follow(browser, browser.submit(form, matadors=""))
    page = follow(browser, browser.submit(activated_form(page, PREFIX + "apply")))
    assert active.state.command_log[-1].command.declaration.matadors is None
    saved = active.path.read_bytes()
    assert saved != before
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    assert localized_server.app_context.managed_stateful.active_session.path.read_bytes() == saved


def test_match_two_digits_then_explicit_null_clearing(localized_server):
    browser = Browser(localized_server)
    form = declaration_form(start_match(browser), "match-declaration")
    page = follow(browser, browser.submit(form, game_type="clubs", matadors="11"))
    active = localized_server.app_context.managed_stateful.active_match
    assert active.workspace.slots[0].observed_game.declaration.matadors == 11
    assert_count(page, "en", session=False, value="11")
    before = active.path.read_bytes()
    response = browser.submit(declaration_form(page, "match-declaration"), game_type="null")
    assert response[0] == 400 and active.path.read_bytes() == before
    page = response[2].decode()
    assert_count(page, "en", session=False, value="11", error=True)
    page = follow(browser, browser.submit(declaration_form(page, "match-declaration"), matadors=""))
    accepted = active.workspace.slots[0].observed_game.declaration
    assert accepted.game_type == "null" and accepted.matadors is None
    saved = active.path.read_bytes()
    follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    assert localized_server.app_context.managed_stateful.active_match.path.read_bytes() == saved
