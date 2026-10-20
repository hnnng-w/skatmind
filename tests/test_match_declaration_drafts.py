"""Native ownership and exact-source draft-only evidence transport with real files."""

from html.parser import HTMLParser

import pytest
from test_direct_match_evidence import started
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


class NativePage(HTMLParser):
    """Successful controls use native form ownership, including external submitters."""

    def __init__(self, html):
        super().__init__()
        self.forms, self.controls = [], []
        self.current = self.select = None
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "form":
            assert self.current is None, "Nested forms are invalid"
            self.current = attrs
            self.forms.append(attrs)
        if tag in {"input", "select", "button", "textarea"}:
            control = {**attrs, "tag": tag, "parent": self.current}
            self.controls.append(control)
            if tag == "select":
                self.select = control
                control["options"] = []
        if tag == "option" and self.select is not None:
            self.select["options"].append(attrs.get("value", ""))
            if "value" not in self.select or "selected" in attrs:
                self.select["value"] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None
        if tag == "select":
            self.select = None

    def owner(self, control):
        if "form" in control:
            return next(form for form in self.forms if form.get("id") == control["form"])
        return control["parent"]

    def field(self, name):
        return next(c for c in self.controls if c.get("name") == name)

    def enter(self, **values):
        for name, value in values.items():
            control = self.field(name)
            if control.get("type") == "checkbox":
                control.pop("checked", None)
                if value:
                    control["checked"] = ""
            else:
                assert control["tag"] != "select" or value in control["options"]
                control["value"] = value

    def button(self, action):
        button = next((c for c in self.controls if c["tag"] == "button"
                       and c.get("name") == "recording_action" and c.get("value") == action), None)
        if button is not None:
            return button
        # Baseline emitted independent forms, without synthesizing draft fields.
        marker = "operation" if action == "set_declaration" else "card_evidence_form"
        field = next(c for c in self.controls if c.get("name") == marker
                     and c.get("value") == action)
        return next(c for c in self.controls if c["tag"] == "button"
                    and self.owner(c) is self.owner(field))

    def choose(self, prefix, cards):
        button = self.button(prefix + "_selected")
        owner = self.owner(button)
        name = "evidence_" + prefix
        if not any(c.get("name") == name for c in self.controls):
            name = "cards"
        for control in self.controls:
            if control.get("name") == name and self.owner(control) is owner:
                control.pop("checked", None)
                if control.get("value") in cards:
                    control["checked"] = ""

    def submission(self, action):
        button = self.button(action)
        owner = self.owner(button)
        values = {}
        for control in self.controls:
            name = control.get("name")
            if not name or "disabled" in control or self.owner(control) is not owner:
                continue
            if control["tag"] == "button" and control is not button:
                continue
            if control.get("type") in {"checkbox", "radio"} and "checked" not in control:
                continue
            value = control.get("value", "on" if control.get("type") == "checkbox" else "")
            if name in values:
                prior = values[name]
                values[name] = [*(prior if isinstance(prior, list) else [prior]), value]
            else:
                values[name] = value
        return button.get("formaction", owner["action"]), values

    def submit(self, browser, action):
        route, values = self.submission(action)
        return browser.request("POST", route, values)


def test_native_evidence_preserves_unsaved_declaration(localized_server):
    browser = Browser(localized_server)
    page = NativePage(started(browser))
    declarer = page.field("declarer_player_id")["options"][2]
    page.enter(declarer_player_id=declarer, game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    assert len([c for c in page.controls if c.get("name") == "declarer_player_id"]) == 1
    for action in ("set_declaration", "perspective_hand_selected", "original_skat_selected",
                   "discarded_cards_selected", "discarded_cards_empty"):
        assert page.owner(page.button(action)) is page.owner(page.field("declarer_player_id"))
    active = localized_server.app_context.managed_stateful.active_match
    revision = active.workspace.revision
    returned = NativePage(follow(browser, page.submit(browser, "discarded_cards_selected")))
    game = active.workspace.slots[0].observed_game
    assert game.declarer_player_id is game.declaration is None
    assert set(game.discarded_cards) == {"H7", "D7"}
    assert active.workspace.revision == revision + 1
    assert returned.field("declarer_player_id")["value"] == declarer
    assert returned.field("game_type")["value"] == "grand"
    assert returned.field("bid_value")["value"] == "18"


@pytest.mark.parametrize("locale", ("en", "de"))
def test_evidence_error_noop_explicit_save_and_language(localized_server, monkeypatch, locale):
    from test_session_recorded_review_web import Forms

    import skatmind.capture_web.context as capture

    browser = Browser(localized_server)
    page = NativePage(started(browser, locale=locale))
    active = localized_server.app_context.managed_stateful.active_match
    calls = []
    real = capture.save_match_workspace_file_v1
    def save(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    declarer = page.field("declarer_player_id")["options"][2]
    page.enter(declarer_player_id=declarer, game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    html = follow(browser, page.submit(browser, "discarded_cards_selected"))
    assert len(calls) == 1
    page = NativePage(html)
    page.choose("discarded_cards", {"H7"})
    status, _, raw = page.submit(browser, "discarded_cards_selected")
    assert status == 400 and len(calls) == 1
    html = raw.decode()
    page = NativePage(html)
    assert page.field("bid_value")["value"] == "18"
    assert 'aria-invalid="true"' in html and 'class="error-summary"' in html
    assert page.submission("discarded_cards_selected")[1]["evidence_discarded_cards"] == "H7"
    # Native language return uses the already submitted, source-checked draft.
    html = follow(browser, browser.submit(Forms(html).find("/actions/profile/language"),
                                         language="de" if locale == "en" else "en"))
    page = NativePage(html)
    assert page.field("bid_value")["value"] == "18"
    page.choose("discarded_cards", {"H7", "D7"})
    html = follow(browser, page.submit(browser, "discarded_cards_selected"))
    assert len(calls) == 1
    page = NativePage(html)
    assert page.field("bid_value")["value"] == "18"
    assert active.workspace.slots[0].observed_game.declaration is None
    html = follow(browser, page.submit(browser, "set_declaration"))
    assert len(calls) == 2
    assert active.workspace.slots[0].observed_game.declaration.bid_value == 18
    follow(browser, NativePage(html).submit(browser, "set_declaration"))
    assert len(calls) == 2


@pytest.mark.parametrize("prefix,cards", (
    ("perspective_hand", ("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "S10")),
    ("original_skat", ("H7", "D7")), ("discarded_cards", ("H7", "D7")),
))
@pytest.mark.parametrize("draft", (
    {"game_type": "", "bid_value": "", "matadors": "", "hand_game": False},
    {"game_type": "null", "bid_value": "-3", "matadors": "<script>x</script>",
     "hand_game": True, "schwarz_announced": True},
))
def test_all_editors_withdrawals_and_semantically_invalid_drafts(
    localized_server, prefix, cards, draft,
):
    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.enter(**draft)
    page.choose(prefix, cards)
    html = follow(browser, page.submit(browser, prefix + "_selected"))
    page = NativePage(html)
    for name, expected in draft.items():
        assert ("checked" in page.field(name) if isinstance(expected, bool)
                else page.field(name)["value"]) == expected
    assert "<script>x</script>" not in html
    active = localized_server.app_context.managed_stateful.active_match
    assert active.workspace.slots[0].observed_game.declaration is None
    html = follow(browser, page.submit(browser, prefix + "_unknown"))
    assert NativePage(html).field("bid_value")["value"] == draft["bid_value"]
    if prefix == "discarded_cards":
        html = follow(browser, NativePage(html).submit(browser, "discarded_cards_empty"))
        assert active.workspace.slots[0].observed_game.discarded_cards == ()


@pytest.mark.parametrize("change", (
    "replay", "expiry", "movement", "reload", "unrelated", "declaration"))
def test_successor_handoff_never_overwrites_changed_source(localized_server, change):
    from test_match_recording_recovery_web import operation_form

    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.enter(game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    response = page.submit(browser, "discarded_cards_selected")
    assert response[0] == 303
    active = localized_server.app_context.managed_stateful.active_match
    target = response[1]["location"].split("#")[0]
    if change == "replay":
        browser.page(target)
    elif change == "expiry":
        active.declaration_draft_return.created -= 61
    elif change == "movement":
        browser.page("/matches/position/2")
        browser.page("/matches/position/1")
    elif change == "reload":
        # A normal GET (including browser reload) invalidates an undelivered return.
        browser.page("/matches/position/1")
    elif change == "unrelated":
        html = browser.page("/matches/position/1")
        follow(browser, browser.submit(operation_form(html, "set_game_timecode"),
                                       game_timecode_start="1"))
    else:
        current = NativePage(browser.page("/matches/position/1"))
        current.enter(declarer_player_id=current.field("declarer_player_id")["options"][1],
                      game_type="null", bid_value="23")
        follow(browser, current.submit(browser, "set_declaration"))
    before = active.path.read_bytes()
    status, _, raw = browser.request("GET", target)
    assert status == 409
    assert "draft could not be restored" in raw.decode()
    assert NativePage(raw.decode()).field("bid_value")["value"] != "18"
    assert active.path.read_bytes() == before


def test_recoverable_save_failure_preserves_draft_without_publication(
    localized_server, monkeypatch,
):
    import skatmind.capture_web.context as capture

    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.enter(game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    def fail(*args, **kwargs):
        raise OSError("Synthetic prepublication storage failure")
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", fail)
    status, _, raw = page.submit(browser, "discarded_cards_selected")
    assert status == 409 and active.path.read_bytes() == before
    assert NativePage(raw.decode()).field("bid_value")["value"] == "18"
    assert active.workspace.slots[0].observed_game.declaration is None


def test_accepted_flags_and_numbers_can_be_explicitly_emptied_only_in_draft(localized_server):
    import re

    browser = Browser(localized_server)
    page = NativePage(started(browser, context="hand"))
    active = localized_server.app_context.managed_stateful.active_match
    declaration = active.workspace.slots[0].observed_game.declaration
    assert declaration.hand_game
    page.enter(declarer_player_id="", game_type="", hand_game=False, bid_value="", matadors="")
    page.choose("original_skat", {"H7", "D7"})
    html = follow(browser, page.submit(browser, "original_skat_selected"))
    returned = NativePage(html)
    assert returned.field("declarer_player_id")["value"] == ""
    assert returned.field("game_type")["value"] == ""
    assert "checked" not in returned.field("hand_game")
    assert active.workspace.slots[0].observed_game.declaration == declaration
    summary = re.search(r'<section class="accepted-declaration">.*?</section>', html, re.S)[0]
    assert "Grand" in summary and "Yes" in summary


@pytest.mark.parametrize("failure", ("expiry", "replay", "return_expiry"))
def test_native_language_draft_lifetime_is_not_renewed(localized_server, failure):
    from dataclasses import replace

    from test_session_recorded_review_web import Forms

    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.enter(game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    html = follow(browser, page.submit(browser, "discarded_cards_selected"))
    form = Forms(html).find("/actions/profile/language")
    context = localized_server.app_context.language_context
    key = form["values"]["_frontend_language_context"]
    saved = localized_server.app_context.managed_stateful.active_match.path.read_bytes()
    if failure == "expiry":
        retained = context.pages[key]
        context.pages[key] = replace(retained,
            native_match_draft_deadline=retained.native_match_draft_deadline - 61)
    else:
        response = browser.submit(form, language="de")
        assert response[0] == 303
        if failure == "return_expiry":
            retained, values = context.pending
            context.pending = (replace(retained,
                native_match_draft_deadline=retained.native_match_draft_deadline - 61), values)
            status, _, raw = browser.request("GET", response[1]["location"])
            assert status == 409
            assert "Entwurf" in raw.decode()
            return
        follow(browser, response)
    assert browser.submit(form, language="en")[0] == 409
    assert localized_server.app_context.managed_stateful.active_match.path.read_bytes() == saved


def test_enhanced_language_submission_becomes_current_native_draft(localized_server):
    import json
    import re

    from test_session_recorded_review_web import Forms

    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.enter(game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    html = follow(browser, page.submit(browser, "discarded_cards_selected"))
    block = re.search(r'<form id="match-recording-input".*?</form>', html, re.S)[0]
    identity = re.search(r'data-language-form="([^"]+)"', block)[1]
    raw = json.dumps({"forms": [{"form": identity, "values": {"bid_value": ["19"]}}],
                      "disclosures": [False] * html.count('<details')})
    html = follow(browser, browser.submit(Forms(html).find("/actions/profile/language"),
                                         language="de", _frontend_language_values=raw))
    assert NativePage(html).field("bid_value")["value"] == "19"
    html = follow(browser, browser.submit(Forms(html).find("/actions/profile/language"),
                                         language="en"))
    assert NativePage(html).field("bid_value")["value"] == "19"
    assert localized_server.app_context.managed_stateful.active_match.workspace.slots[
        0].observed_game.declaration is None


@pytest.mark.parametrize("kind", ("replacement", "declaration", "evidence", "reopen", "match"))
def test_pending_return_checks_actual_successor_not_revision_alone(localized_server, kind):
    from test_session_recorded_review_web import Forms

    from skatmind.match_capture_application import set_match_capture_original_skat_v1
    from skatmind.match_workspace_contracts import _build_match_workspace_v1
    from skatmind.match_workspace_persistence import (
        build_match_workspace_persistence_document_v1,
        save_match_workspace_file_v1,
    )

    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.enter(game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    html = follow(browser, page.submit(browser, "discarded_cards_selected"))
    other_tab = NativePage(html)
    response = NativePage(html).submit(browser, "discarded_cards_selected")
    active = localized_server.app_context.managed_stateful.active_match
    returned = active.declaration_draft_return
    if kind == "replacement":
        result = set_match_capture_original_skat_v1(active.workspace, match_position=1,
            cards=("H8", "D8"), expected_revision=active.workspace.revision)
        workspace = result.workspace_change.workspace
        workspace = _build_match_workspace_v1(revision=active.workspace.revision,
            match_definition=workspace.match_definition, slots=workspace.slots)
        save_match_workspace_file_v1(active.path,
            build_match_workspace_persistence_document_v1(workspace),
            expected_content_fingerprint=active.capture.content_fingerprint)
    elif kind == "declaration":
        other_tab.enter(declarer_player_id=other_tab.field("declarer_player_id")["options"][1],
                        game_type="null", bid_value="23")
        assert other_tab.submit(browser, "set_declaration")[0] == 303
        assert active.declaration_draft_return is returned
    elif kind == "evidence":
        other_tab.choose("original_skat", {"H8", "D8"})
        assert other_tab.submit(browser, "original_skat_selected")[0] == 303
    elif kind == "reopen":
        category = browser.page("/matches")
        assert browser.submit(Forms(category).find("/matches/open"))[0] == 303
    else:
        started(browser)
    before = active.path.read_bytes()
    status, _, raw = browser.request("GET", response[1]["location"].split("#")[0])
    assert status == 409 and "draft could not be restored" in raw.decode()
    assert active.path.read_bytes() == before


def test_competing_native_save_and_evidence_are_serialized(localized_server):
    from concurrent.futures import ThreadPoolExecutor

    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.enter(declarer_player_id=page.field("declarer_player_id")["options"][1],
               game_type="grand", bid_value="18")
    page.choose("discarded_cards", {"H7", "D7"})
    active = localized_server.app_context.managed_stateful.active_match
    revision = active.workspace.revision
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda action: page.submit(browser, action),
                                 ("set_declaration", "discarded_cards_selected")))
    assert sorted(result[0] for result in results) == [303, 409]
    assert active.workspace.revision == revision + 1
    game = active.workspace.slots[0].observed_game
    assert (game.declaration is None) != (game.discarded_cards is None)


@pytest.mark.parametrize("fault", (
    "missing", "ambiguous", "extra", "duplicate", "oversize", "foreign"))
def test_malformed_shared_transport_cannot_mutate(localized_server, fault):
    browser = Browser(localized_server)
    page = NativePage(started(browser))
    page.choose("discarded_cards", {"H7", "D7"})
    route, values = page.submission("discarded_cards_selected")
    if fault == "missing":
        values.pop("recording_action")
    elif fault == "ambiguous":
        values["recording_action"] = ["discarded_cards_selected", "set_declaration"]
    elif fault == "extra":
        values["confirm_clear"] = "on"
    elif fault == "duplicate":
        values["bid_value"] = ["18", "18"]
    elif fault == "oversize":
        values["bid_value"] = "9" * 8192
    else:
        values["managed_handle"] = "0" * 64
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    assert browser.request("POST", route, values)[0] == (413 if fault == "oversize" else
                                                        409 if fault == "foreign" else 400)
    assert active.path.read_bytes() == before
