"""Language-only delivery is one-shot, source-bound, and never a Product action."""

import json
import re
from html import unescape
from importlib.resources import files

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def skat_entry(browser):
    page = create(browser)
    response = browser.submit(Forms(page).find("/sessions/cards"),
        cards="CA C10 CK CQ CJ SA S10 SK SQ SJ".split())
    assert response[1]["location"] == "/sessions/current#session-recording"
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="clubs", hand_game="false", bid_value="18")
    return browser.page()


def view_envelope(page, *, anchor="top", offset=0, locale="de", cards=("H7",)):
    value = json.loads(envelope(page, "/sessions/cards", {"cards": list(cards)}))
    value["view"] = {"anchor": anchor, "offset": offset, "x": 0, "focus": locale}
    return value


def return_data(page):
    found = re.search(r'<meta name="language-return" content="([^"]+)">', page)
    return None if found is None else json.loads(unescape(found[1]))


@pytest.mark.parametrize("anchor,offset", (("top", 0), ("id:session-recording", -135.25)))
def test_real_http_view_return_keeps_unsent_and_rejected_values_without_saves(
    localized_server, monkeypatch, anchor, offset,
):
    import skatmind.api.v1.session.files as session_files
    import skatmind.app_web.execution as execution

    browser = Browser(localized_server)
    page = skat_entry(browser)
    active = localized_server.app_context.managed_stateful.active_session
    document, saved = active.document, active.path.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Language change executed Product work")
    monkeypatch.setattr(session_files, "save_session_file", forbidden)
    monkeypatch.setattr(execution, "execute", forbidden)
    rejected = browser.submit(Forms(page).find("/sessions/cards"), cards=["H7", "H7"])
    assert rejected[0] == 400 and b"autofocus" in rejected[2]
    page = rejected[2].decode()
    for locale in ("de", "en"):
        value = view_envelope(page, anchor=anchor, offset=offset, locale=locale)
        response = enhanced_switch(browser, page, json.dumps(value), locale)
        assert response[0] == 303 and "#" not in response[1]["location"]
        assert re.fullmatch(r"/sessions/current\?_language_return=[0-9a-f]{64}",
                            response[1]["location"])
        page = follow(browser, response)
        assert return_data(page)["view"] == value["view"]
        assert page.index('name="language-return"') < page.index(
            '<script src="/matches/assets/capture.js"></script>') < page.index("</head>")
        assert "autofocus" not in page
        assert 'class="error-summary"' in page and 'href="#' in page
        assert Forms(page).find("/sessions/cards")["values"]["cards"] == "H7"
        assert 'data-operation-feedback' not in page
        assert active.document is document and active.path.read_bytes() == saved
        # Both refresh/ordinary navigation and a copied/old delivery URL are inert.
        assert return_data(browser.page()) is None
        replay = browser.request("GET", response[1]["location"])
        assert replay[0] == 303 and replay[1]["location"] == "/sessions/current"
        assert return_data(follow(browser, replay)) is None


@pytest.mark.parametrize("change", (
    {"anchor": "#session-recording"}, {"anchor": "id:foreign-recording"},
    {"anchor": '<script>alert(1)</script>'}, {"anchor": []},
    {"offset": float("nan")}, {"offset": float("inf")}, {"offset": -8193},
    {"offset": 8193}, {"offset": True}, {"offset": "12"}, {"offset": None},
    {"x": -1}, {"x": 1_000_001}, {"x": float("-inf")}, {"focus": "fr"},
    {"focus": "en"}, {"selector": "body"}, {"anchor": "x" * 262145},
))
def test_untrusted_view_rejected_before_language_save(localized_server, change):
    browser = Browser(localized_server)
    page = skat_entry(browser)
    value = view_envelope(page)
    value["view"].update(change)
    profile = localized_server.app_context.frontend_profile
    status, _, body = enhanced_switch(browser, page, json.dumps(value))
    assert status in (400, 413)
    assert localized_server.app_context.frontend_profile is profile
    assert return_data(body.decode()) is None
    assert b"autofocus" in body


def test_delivery_cannot_be_consumed_by_an_unrelated_tab_or_page(localized_server):
    browser = Browser(localized_server)
    page = skat_entry(browser)
    response = enhanced_switch(browser, page, json.dumps(view_envelope(page)))
    token = response[1]["location"].split("?", 1)[1]
    other_tab = Browser(localized_server)
    assert return_data(other_tab.page()) is None
    assert return_data(other_tab.page("/about")) is None
    mismatch = other_tab.request("GET", "/about?" + token)
    assert mismatch[0] == 303 and mismatch[1]["location"] == "/about"
    assert return_data(follow(browser, response))["view"]["anchor"] == "top"


@pytest.mark.parametrize("change", ("source", "reopen", "expiry", "profile", "manifest"))
def test_view_is_not_restored_after_context_changes(localized_server, monkeypatch, change):
    from dataclasses import replace

    import skatmind.app_web.language_context as binding

    browser = Browser(localized_server)
    page = skat_entry(browser)
    response = enhanced_switch(browser, page, json.dumps(view_envelope(page)))
    context = localized_server.app_context
    if change == "source":
        browser.command("record_dealt_card", card="H8")
    elif change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    elif change == "expiry":
        now = binding.time.monotonic()
        monkeypatch.setattr(binding.time, "monotonic", lambda: now + 1801)
    elif change == "profile":
        from skatmind.app_web.frontend_profile_operations import set_frontend_language_v1
        set_frontend_language_v1(context, language="en",
                                 expected_generation=context.frontend_profile.generation)
    else:
        retained, values = context.language_context.pending
        context.language_context.pending = (
            replace(retained, manifest=replace(retained.manifest, view_ids=())), values)
    status, _, body = browser.request("GET", response[1]["location"])
    assert status == 409 and return_data(body.decode()) is None
    assert b"autofocus" in body and b"href=" in body
    assert context.language_context.pending is None


@pytest.mark.parametrize("route", ("/", "/about", "/review", "/review/recorded", "/settings"))
def test_shared_safe_html_callers_use_the_same_one_use_delivery(localized_server, route):
    browser = Browser(localized_server)
    page = browser.page(route)
    value = {"forms": [], "disclosures": [False] * len(re.findall(r"<details\b", page)),
             "view": {"anchor": "top", "offset": 0, "x": 0, "focus": "de"}}
    response = enhanced_switch(browser, page, json.dumps(value))
    assert response[0] == 303 and response[1]["location"].split("?", 1)[0] == route
    assert "#" not in response[1]["location"]
    returned = follow(browser, response)
    assert return_data(returned)["view"] == value["view"]
    assert 'rel="expect" blocking="render"' in returned
    assert returned.index('id="language-view-ready"') > returned.index('</main>')
    # Query support is delivery-only; it cannot widen POST return_to or authorize GET.
    form = Forms(returned).find("/actions/profile/language")
    assert browser.submit(form, language="en", return_to=response[1]["location"])[0] == 400
    assert browser.request("GET", response[1]["location"], headers={"Cookie": ""})[0] == 403


def test_native_feedback_return_and_served_initialization(localized_server):
    browser = Browser(localized_server)
    page = skat_entry(browser)
    status, _, raw = browser.submit(Forms(page).find("/sessions/cards"), cards=["H7", "H7"])
    assert status == 400
    page = raw.decode()
    links = re.findall(r'href="(#[^"]+)"', page)
    response = browser.submit(Forms(page).find("/actions/profile/language"), language="de")
    assert response[1]["location"] == "/sessions/current"
    page = follow(browser, response)
    assert return_data(page)["view"] is None
    assert "autofocus" not in page
    assert re.findall(r'href="(#[^"]+)"', page) == links
    status, _, resource = browser.request("GET", "/matches/assets/capture.js")
    assert status == 200 and resource == files("skatmind.app_web").joinpath(
        "assets/workflow.js").read_bytes()
    script = resource.decode()
    assert script.index('classList.add("operation-overlays")') < script.index("DOMContentLoaded")
    assert script.count('addEventListener("DOMContentLoaded"') == 1
    assert "sessionStorage" not in script and "localStorage" not in script


@pytest.mark.parametrize("stage", ("after_save", "during_render"))
def test_competing_language_generation_cannot_publish_a_mismatched_view(
    localized_server, monkeypatch, stage,
):
    import skatmind.app_web.server as server_module
    from skatmind.app_web.frontend_profile_operations import set_frontend_language_v1

    browser = Browser(localized_server)
    page = skat_entry(browser)
    context = localized_server.app_context
    if stage == "after_save":
        def interleaved(*args, **kwargs):
            result = set_frontend_language_v1(*args, **kwargs)
            set_frontend_language_v1(context, language="en",
                                     expected_generation=context.frontend_profile.generation)
            return result
        monkeypatch.setattr(server_module, "set_frontend_language_v1", interleaved)
    response = enhanced_switch(browser, page, json.dumps(view_envelope(page)))
    if stage == "during_render":
        original = server_module.instrument_language_forms_v1
        def changed_generation(html):
            set_frontend_language_v1(context, language="en",
                                     expected_generation=context.frontend_profile.generation)
            return original(html)
        monkeypatch.setattr(server_module, "instrument_language_forms_v1", changed_generation)
        response = browser.request("GET", response[1]["location"])
    assert response[0] == 409 and return_data(response[2].decode()) is None
    assert b"autofocus" in response[2]
