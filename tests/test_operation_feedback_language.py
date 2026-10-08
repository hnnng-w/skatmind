"""Actual language POST/final-response continuity without another Product operation."""

import json
import re
from dataclasses import replace
from html import escape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_view_continuity import return_data
from test_learning_direct_entry_web import (
    add_form,
    build,
    create_collection,
    downloads,
    saved_bytes,
    source_handle,
)
from test_match_game_navigation_web import create_empty
from test_match_recording_recovery_web import follow
from test_operation_feedback_web import notices
from test_recorded_review_navigation import saved_partial_match
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def presentation(page, remaining=5000, locale="de"):
    value = {"forms": [], "disclosures": [False] * len(re.findall(r"<details\b", page)),
             "view": {"anchor": "top", "offset": 0, "x": 0, "focus": locale}}
    if remaining is not None:
        value["feedback_remaining_ms"] = remaining
    return value


def bound_page(server, page):
    token = Forms(page).find("/actions/profile/language")["values"]["_frontend_language_context"]
    return server.app_context.language_context.pages[token]


def continued(page, key, locale, remaining, **values):
    row, = notices(page)
    assert row["text"] == text(locale, "feedback." + key, **values)
    assert row["attrs"]["data-dismiss-label"] == text(locale, "feedback.dismiss")
    assert float(row["attrs"]["data-feedback-remaining-ms"]) == remaining
    # Enhancement alone reveals continuation; native/failed-load fallback cannot replay it.
    assert "hidden" in row["attrs"] and "data-feedback-continuation" in row["attrs"]
    assert row["attrs"]["aria-live"] == "polite" and "autofocus" not in page
    assert len(notices(page)) == 1


@pytest.mark.parametrize("family,key", (("session", "session_created"),
    ("match", "match_created"), ("learning", "learning_created")))
def test_shared_delivery_continues_both_directions_and_noop_without_renewal(
    localized_server, monkeypatch, family, key,
):
    import skatmind.api.v1.session.files as session_files
    import skatmind.app_web.execution as execution

    browser = Browser(localized_server)
    page = (create(browser) if family == "session" else create_empty(browser, "en")
            if family == "match" else create_collection(browser))
    active = getattr(localized_server.app_context.managed_stateful, "active_" + family)
    before = saved_bytes(active.path) if family == "learning" else active.path.read_bytes()
    receipt = bound_page(localized_server, page).feedback.receipt
    operation = active.operation_feedback.attempt
    def forbidden(*args, **kwargs):
        pytest.fail("Language presentation executed Product work")
    monkeypatch.setattr(session_files, "save_session_file", forbidden)
    monkeypatch.setattr(execution, "execute", forbidden)
    for locale, remaining in (("de", 5032.75), ("en", 3100.5), ("en", 1900)):
        response = enhanced_switch(browser, page, json.dumps(presentation(page, remaining, locale)),
                                   locale)
        assert response[0] == 303
        page = follow(browser, response)
        continued(page, key, locale, remaining)
        binding = bound_page(localized_server, page).feedback
        assert binding.receipt is receipt and binding.remaining_ms == remaining
        assert active.operation_feedback.pending is None
        assert active.operation_feedback.attempt is operation
    after = saved_bytes(active.path) if family == "learning" else active.path.read_bytes()
    assert after == before


def test_real_card_save_name_escaping_pending_values_and_view(localized_server):
    browser = Browser(localized_server)
    label = '<Alex & "Player">'
    form = Forms(browser.page("/sessions")).find("/sessions/create")
    page = follow(browser, browser.submit(form, game_name="Synthetic feedback",
        forehand_name=label, middlehand_name="Boris", rearhand_name="Clara",
        capture_mode="live", perspective_seat="forehand", setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/sessions/create"),
                                         setup_action="create"))
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=["CA"]))
    active = localized_server.app_context.managed_stateful.active_session
    original, accepted = active.document, active.path.read_bytes()
    value = presentation(page, 5000)
    value.update(json.loads(envelope(page, "/sessions/cards", {"cards": ["H7"]})))
    value["view"].update(anchor="id:session-recording", offset=-123.5)
    page = follow(browser, enhanced_switch(browser, page, json.dumps(value)))
    continued(page, "initial_cards", "de", 5000, count=1, player=label)
    assert escape(label, quote=True) in page and label not in page
    assert Forms(page).find("/sessions/cards")["values"]["cards"] == "H7"
    assert return_data(page)["view"] == value["view"]
    assert active.document is original and active.path.read_bytes() == accepted
    assert active.state.revision == 2


@pytest.mark.parametrize("value", (-1, 8001, 10**1000, True, "5000", None, [], {},
                                   float("nan"), float("inf"), float("-inf")))
def test_invalid_timing_consumes_authorization_and_keeps_error_priority(localized_server, value):
    browser = Browser(localized_server)
    page = create(browser)
    profile = localized_server.app_context.frontend_profile
    data = presentation(page)
    data["feedback_remaining_ms"] = value
    status, _, raw = enhanced_switch(browser, page, json.dumps(data))
    assert status == 400 and not notices(raw.decode()) and b"autofocus" in raw
    assert localized_server.app_context.frontend_profile is profile
    assert bound_page(localized_server, page).feedback is None
    assert enhanced_switch(browser, page, json.dumps(presentation(page)))[0] in (400, 409)


@pytest.mark.parametrize("extra", ({"message": "Success"}, {"html": "<b>Saved</b>"},
    {"message_key": "feedback.play"}, {"operation_identity": "foreign"}))
def test_client_cannot_author_receipt(localized_server, extra):
    browser = Browser(localized_server)
    page = create(browser)
    status, _, raw = enhanced_switch(browser, page, json.dumps(presentation(page) | extra))
    assert status == 400 and not notices(raw.decode())


@pytest.mark.parametrize("mode", ("native", "absent", "exhausted", "other_page"))
def test_no_visible_authorized_feedback_does_not_regenerate(localized_server, mode):
    browser = Browser(localized_server)
    page = create(browser)
    if mode == "other_page":
        page = browser.page()
        response = enhanced_switch(browser, page, json.dumps(presentation(page)))
        assert response[0] == 400 and not notices(response[2].decode())
        return
    response = (browser.submit(Forms(page).find("/actions/profile/language"), language="de")
        if mode == "native" else enhanced_switch(browser, page,
            json.dumps(presentation(page, 0 if mode == "exhausted" else None))))
    page = follow(browser, response)
    assert not notices(page) and bound_page(localized_server, page).feedback is None


def test_return_and_submission_are_once_only_even_for_noop_locale(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    # No generation change can be relied on to block duplicate no-op submissions.
    response = enhanced_switch(browser, page, json.dumps(presentation(page, 5000, "en")), "en")
    assert response[0] == 303
    returned = follow(browser, response)
    continued(returned, "session_created", "en", 5000)
    replay = browser.request("GET", response[1]["location"])
    assert replay[0] == 303 and not notices(follow(browser, replay))
    assert not notices(browser.page())
    status, _, raw = enhanced_switch(browser, page,
        json.dumps(presentation(page, 5000, "en")), "en")
    assert status == 400 and not notices(raw.decode())


def test_other_tab_cannot_acquire_or_consume_pending_continuation(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    response = enhanced_switch(browser, page, json.dumps(presentation(page)))
    other = Browser(localized_server)
    ordinary = other.page()
    assert not notices(ordinary) and bound_page(localized_server, ordinary).feedback is None
    assert not notices(other.page("/about"))
    continued(follow(browser, response), "session_created", "de", 5000)


def test_cannot_increase_a_continued_budget(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    page = follow(browser, enhanced_switch(browser, page, json.dumps(presentation(page, 2300))))
    status, _, raw = enhanced_switch(browser, page,
        json.dumps(presentation(page, 2301, "en")), "en")
    assert status == 400 and not notices(raw.decode())


def test_navigation_latency_does_not_spend_active_display_budget(localized_server, monkeypatch):
    import skatmind.app_web.operation_feedback as feedback

    browser = Browser(localized_server)
    page = create(browser)
    receipt = bound_page(localized_server, page).feedback.receipt
    monkeypatch.setattr(feedback.time, "monotonic", lambda: receipt.expires_at - 30)
    response = enhanced_switch(browser, page, json.dumps(presentation(page, 4750)))
    monkeypatch.setattr(feedback.time, "monotonic", lambda: receipt.expires_at - 10)
    page = follow(browser, response)
    continued(page, "session_created", "de", 4750)
    assert bound_page(localized_server, page).feedback.receipt is receipt


@pytest.mark.parametrize("stage", ("before_post", "during_navigation", "after_repeated_switch"))
def test_original_monotonic_deadline_is_never_renewed(localized_server, monkeypatch, stage):
    import skatmind.app_web.operation_feedback as feedback

    browser = Browser(localized_server)
    page = create(browser)
    deadline = bound_page(localized_server, page).feedback.receipt.expires_at
    monkeypatch.setattr(feedback.time, "monotonic", lambda: deadline - 5)
    if stage == "after_repeated_switch":
        page = follow(browser, enhanced_switch(browser, page, json.dumps(presentation(page))))
        assert bound_page(localized_server, page).feedback.receipt.expires_at == deadline
    if stage != "during_navigation":
        monkeypatch.setattr(feedback.time, "monotonic", lambda: deadline)
    response = enhanced_switch(browser, page, json.dumps(presentation(page, 4900, "en")), "en")
    monkeypatch.setattr(feedback.time, "monotonic", lambda: deadline)
    assert not notices(follow(browser, response))


@pytest.mark.parametrize("change", (
    "attempt", "source", "rejection", "reopen", "file", "profile", "manifest",
))
def test_source_or_error_wins_at_final_return(localized_server, change):
    from skatmind.app_web.frontend_profile_operations import set_frontend_language_v1

    browser = Browser(localized_server)
    page = create(browser)
    response = enhanced_switch(browser, page, json.dumps(presentation(page)))
    context = localized_server.app_context
    active = context.managed_stateful.active_session
    if change == "attempt":
        active.operation_feedback.begin()
    elif change == "source":
        browser.command("record_dealt_card", card="H8")
    elif change == "rejection":
        accepted = active.path.read_bytes()
        status, _, raw = browser.submit(Forms(page).find("/sessions/cards"), cards=["CA", "CA"])
        assert status == 400 and not notices(raw.decode())
        assert Forms(raw.decode()).find("/sessions/cards")["values"]["cards"] == "CA"
        assert active.path.read_bytes() == accepted
    elif change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    elif change == "file":
        active.path.write_bytes(b"{}")  # Disposable fixture only.
    elif change == "profile":
        set_frontend_language_v1(context, language="en",
                                expected_generation=context.frontend_profile.generation)
    else:
        page, values = context.language_context.pending
        context.language_context.pending = (
            replace(page, manifest=replace(page.manifest, view_ids=())), values)
    status, _, raw = browser.request("GET", response[1]["location"])
    assert status == (200 if change == "attempt" else 409)
    assert not notices(raw.decode())
    if status == 409:
        assert b"autofocus" in raw


def test_learning_prepared_results_and_downloads_survive_continuation(localized_server):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = build(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    artifacts, result = active.corpus.prepared_artifacts, active.last_result
    before, accepted = downloads(browser), saved_bytes(active.path)
    page = follow(browser, enhanced_switch(browser, page, json.dumps(presentation(page))))
    continued(page, "prepared", "de", 5000)
    assert active.corpus.prepared_artifacts is artifacts and active.last_result is result
    assert downloads(browser) == before and saved_bytes(active.path) == accepted
