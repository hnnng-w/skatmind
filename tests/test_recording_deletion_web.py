"""Destructive operations use only pytest's disposable synthetic managed homes."""

from __future__ import annotations

import http.client
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
from frontend_creation_forms import new_name_roster
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.context import AppWebContextV1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def create_recording(browser, family, title="Repeated synthetic title"):
    route = "/sessions/create" if family == "sessions" else "/matches/api/v1/create"
    page = "/sessions" if family == "sessions" else "/matches/new"
    fields = {**new_name_roster(), "perspective_seat": "forehand", "save_players": "on",
              "game_name" if family == "sessions" else "match_title": title}
    from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
    profile = browser.server.app_context.frontend_profile.document
    if profile is not None and profile.known_players:
        for seat, name in zip(("forehand", "middlehand", "rearhand"),
                              ("Alice", "Bob", "Carol"), strict=True):
            player = next(player for player in profile.known_players if player.display_name == name)
            fields.update({f"{seat}_name": "", f"{seat}_mode": "saved",
                           f"{seat}_handle": build_known_player_handle_v1(player.player_id)})
    follow(browser, browser.submit(Forms(browser.page(page)).find(route),
                                   **fields, setup_action="update"))
    form = Forms(browser.page(page)).find(route)
    follow(browser, browser.submit(form, setup_action="create"))
    active = getattr(browser.server.app_context.managed_stateful,
                     "active_session" if family == "sessions" else "active_match")
    return active, form


def deletion_form(browser, family, handle, *, area=None):
    page = browser.page("/review/recorded" if area == "review" else f"/{family}")
    return next(form for form in Forms(page).forms
                if form["action"] == "/recordings/delete/preview"
                and form["values"]["handle"] == handle)


def preview(browser, family, handle, *, area=None):
    return follow(browser, browser.submit(deletion_form(browser, family, handle, area=area)))


@pytest.mark.parametrize("family", ("sessions", "matches"))
@pytest.mark.parametrize("active_target", (False, True))
def test_same_title_native_cancel_then_single_file_removal(localized_server, family, active_target):
    browser = Browser(localized_server)
    first, _ = create_recording(browser, family)
    second, final_create = create_recording(browser, family)
    assert first.path != second.path
    target, other = (second, first) if active_target else (first, second)
    profile = localized_server.app_context.frontend_profile.profile_path
    unchanged_profile, unchanged_other = profile.read_bytes(), other.path.read_bytes()
    assert browser.submit(final_create, setup_action="create")[0] == 409
    page = preview(browser, family, target.handle)
    apply = Forms(page).find("/recordings/delete/apply")
    assert "confirm_delete" not in apply["values"]
    assert "Repeated synthetic title" in page and "Alice" in page
    assert str(target.path) not in page
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/cancel")))
    assert target.path.exists()
    assert browser.submit(apply, confirm_delete="on")[0] == 409
    page = preview(browser, family, target.handle, area="review")
    apply = Forms(page).find("/recordings/delete/apply")
    assert browser.submit(apply)[0] == 400
    assert target.path.exists()
    follow(browser, browser.submit(apply, confirm_delete="on"))
    assert not target.path.exists()
    assert other.path.read_bytes() == unchanged_other
    assert profile.read_bytes() == unchanged_profile
    assert browser.submit(apply, confirm_delete="on")[0] == 409
    managed = localized_server.app_context.managed_stateful
    current = managed.active_session if family == "sessions" else managed.active_match
    assert current is (None if active_target else second)


@pytest.mark.parametrize("family", ("sessions", "matches"))
@pytest.mark.parametrize("change", ("whitespace", "replacement", "missing", "duplicate", "label"))
def test_detected_source_changes_consume_attempt_without_removal(localized_server, family, change):
    browser = Browser(localized_server)
    active, _ = create_recording(browser, family)
    page = preview(browser, family, active.handle)
    form = Forms(page).find("/recordings/delete/apply")
    original = active.path.read_bytes()
    if change == "whitespace":
        active.path.write_bytes(original + b" ")
    elif change == "replacement":
        temporary = active.path.with_suffix(".replacement")
        temporary.write_bytes(original)
        temporary.replace(active.path)
    elif change == "missing":
        active.path.unlink()  # Explicit external-disappearance fixture, not app deletion.
    elif change == "duplicate":
        (active.category_root / "duplicate.json").write_bytes(original)
    else:
        from skatmind.app_web.profile_player_operations import set_managed_item_display_label_v1
        state = localized_server.app_context.frontend_profile
        label = next(label for label in state.document.managed_item_display_labels
                     if label.family == family)
        set_managed_item_display_label_v1(localized_server.app_context,
            label=replace(label, display_name="Changed label"),
            expected_generation=state.generation)
    accepted = active.path.read_bytes() if active.path.exists() else None
    assert browser.submit(form, confirm_delete="on")[0] == 409
    assert localized_server.app_context.recording_deletion.pending is None
    assert not active.retired
    assert (active.path.read_bytes() if active.path.exists() else None) == accepted
    assert browser.submit(form, confirm_delete="on")[0] == 409


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_supersession_expiry_restart_and_reimport_never_refresh_old_tokens(
    localized_server, family,
):
    browser = Browser(localized_server)
    first, _ = create_recording(browser, family)
    second, _ = create_recording(browser, family)
    old = Forms(preview(browser, family, first.handle))
    fresh = Forms(preview(browser, family, second.handle))
    pending = localized_server.app_context.recording_deletion.pending
    assert browser.submit(old.find("/recordings/delete/cancel"))[0] == 409
    assert browser.submit(old.find("/recordings/delete/apply"), confirm_delete="on")[0] == 409
    assert localized_server.app_context.recording_deletion.pending is pending
    follow(browser, browser.submit(fresh.find("/recordings/delete/cancel")))
    form = Forms(preview(browser, family, first.handle)).find("/recordings/delete/apply")
    state = localized_server.app_context.recording_deletion
    state.pending = replace(state.pending, created_at=state.pending.created_at - 1800)
    assert browser.submit(form, confirm_delete="on")[0] == 409
    assert first.path.exists()
    form = Forms(preview(browser, family, first.handle)).find("/recordings/delete/apply")
    saved = first.path.read_bytes()
    follow(browser, browser.submit(form, confirm_delete="on"))
    from test_unified_local_app_managed_items import _multipart
    connection = http.client.HTTPConnection("127.0.0.1", localized_server.port, timeout=30)
    connection.request("POST", f"/{family}/import", body=_multipart(boundary="deletion-import",
        field_name="session_file" if family == "sessions" else "workspace_file", content=saved),
        headers={"Cookie": browser.cookie, "Origin": localized_server.origin,
                 "Content-Type": "multipart/form-data; boundary=deletion-import"})
    response = connection.getresponse()
    assert response.status == 303, response.read()
    response.read()
    connection.close()
    assert first.path.read_bytes() == saved
    assert browser.submit(form, confirm_delete="on")[0] == 409
    new = Forms(preview(browser, family, first.handle)).find("/recordings/delete/apply")
    localized_server.app_context = AppWebContextV1.create(localized_server.app_context.managed_home)
    assert browser.submit(new, confirm_delete="on")[0] == 409
    assert first.path.read_bytes() == saved and second.path.exists()


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_two_real_http_applies_remove_once(localized_server, family, monkeypatch):
    browser = Browser(localized_server)
    active, _ = create_recording(browser, family)
    form = Forms(preview(browser, family, active.handle)).find("/recordings/delete/apply")
    entered, proceed = Event(), Event()
    removals = []
    real = Path.unlink
    def delayed(path, *args, **kwargs):
        if path == active.path:
            entered.set()
            assert proceed.wait(10)
            result = real(path, *args, **kwargs)
            removals.append(path)
            return result
        return real(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", delayed)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(browser.submit, form, confirm_delete="on")
        assert entered.wait(10)
        two = pool.submit(browser.submit, form, confirm_delete="on")
        proceed.set()
        assert sorted((one.result(timeout=15)[0], two.result(timeout=15)[0])) == [303, 409]
    assert removals == [active.path] and not active.path.exists()


@pytest.mark.parametrize("failure", ("permission", "refresh"))
def test_failure_ordering_before_and_after_real_unlink(localized_server, monkeypatch, failure):
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1
    browser = Browser(localized_server)
    active, _ = create_recording(browser, "sessions")
    form = Forms(preview(browser, "sessions", active.handle)).find("/recordings/delete/apply")
    original = active.path.read_bytes()
    if failure == "permission":
        real = Path.unlink
        def refused(path, *args, **kwargs):
            if path == active.path:
                raise PermissionError("private synthetic path must not leak")
            return real(path, *args, **kwargs)
        monkeypatch.setattr(Path, "unlink", refused)
        status, _, body = browser.submit(form, confirm_delete="on")
        assert status == 400 and active.path.read_bytes() == original and not active.retired
    else:
        def failed(*args):
            raise OSError("private synthetic refresh fault")
        monkeypatch.setattr(SkatMindAppWebRequestHandlerV1, "_refresh_category", failed)
        status, headers, _ = browser.submit(form, confirm_delete="on")
        assert status == 303 and headers["location"] == "/recordings/delete"
        body = browser.page(headers["location"]).encode()
        assert b"permanently deleted, but refreshing the list failed" in body
        assert not active.path.exists() and active.retired
    assert b"private synthetic" not in body
    assert browser.submit(form, confirm_delete="on")[0] == 409


@pytest.mark.parametrize("extra", ({"family": "corpora"}, {"return_area": "matches"},
    {"return_area": "https://invalid.test"}, {"generation": "01"}, {"path": "../outside.json"},
    {"handle": ["0" * 64, "1" * 64]}))
def test_exact_preview_fields(localized_server, extra):
    browser = Browser(localized_server)
    active, _ = create_recording(browser, "sessions")
    form = deletion_form(browser, "sessions", active.handle)
    assert browser.submit(form, **extra)[0] == 400
    assert active.path.exists() and localized_server.app_context.recording_deletion.pending is None


@pytest.mark.parametrize("action", ("preview", "apply", "cancel"))
def test_body_method_and_authorization_guards(localized_server, action):
    browser = Browser(localized_server)
    active, _ = create_recording(browser, "sessions")
    route = f"/recordings/delete/{action}"
    assert browser.request("GET", route)[0] == 405
    assert browser.request("POST", route, {"extra": "x" * 8192})[0] == 413
    assert browser.request("POST", route, {}, {"Origin": "null"})[0] == 403
    assert browser.request("POST", route, {}, {"Cookie": ""})[0] == 403
    assert browser.request("POST", route, {}, {"Host": "invalid.test"})[0] == 403
    assert browser.request("POST", route + "?delete=true", {})[0] == 403
    assert browser.request("POST", "/recordings/delete", {})[0] == 405
    assert browser.request("GET", "/recordings/delete?path=anything")[0] == 403
    assert active.path.exists()


@pytest.mark.parametrize("consent", ("true", "yes", "1", "", ["on", "on"]))
def test_consent_is_exact_not_truthy_and_never_reflected(localized_server, consent):
    from test_language_switch_context import switch
    browser = Browser(localized_server)
    active, _ = create_recording(browser, "sessions")
    page = preview(browser, "sessions", active.handle)
    pending = localized_server.app_context.recording_deletion.pending
    form = Forms(page).find("/recordings/delete/apply")
    status, _, body = browser.submit(form, confirm_delete=consent)
    assert status == 400 and active.path.exists()
    for locale in ("de", "en"):
        page = switch(browser, body.decode() if locale == "de" else page, locale)
        assert "confirm_delete" not in Forms(page).find("/recordings/delete/apply")["values"]
        assert localized_server.app_context.recording_deletion.pending is pending
    assert browser.submit(form, confirm_delete="on", extra="unwanted")[0] == 400


def test_real_hardlink_rejected_without_touching_either_name(localized_server):
    browser = Browser(localized_server)
    active, _ = create_recording(browser, "sessions")
    outside = active.category_root.parent / "independent-hardlink"
    os.link(active.path, outside)
    original = outside.read_bytes()
    form = deletion_form(browser, "sessions", active.handle)
    assert browser.submit(form)[0] == 409
    assert outside.read_bytes() == active.path.read_bytes() == original


def test_invalid_duplicate_and_corpus_have_no_delete_controls(localized_server):
    from test_unified_local_app_managed_items import _save_session
    managed = localized_server.app_context.managed_stateful
    root = managed.root("sessions")
    _save_session(root / "one.json")
    _save_session(root / "two.json")
    (root / "invalid.json").write_bytes(b"{}")
    (root / "directory.json").mkdir()
    browser = Browser(localized_server)
    for route in ("/sessions", "/review/recorded", "/learning"):
        assert not any(form["action"] == "/recordings/delete/preview"
                       for form in Forms(browser.page(route)).forms)


def test_exact_private_registry_and_destructive_exclusion():
    from skatmind.app_web.form_registry import (
        capture_safe_submitted_values_v1,
        get_frontend_form_by_key_v1,
    )
    from skatmind.app_web.recording_deletion import DELETION_PAGE, DELETION_POST_ROUTES
    assert DELETION_PAGE == "/recordings/delete"
    assert DELETION_POST_ROUTES == ("/recordings/delete/preview", "/recordings/delete/apply",
                                    "/recordings/delete/cancel")
    for action in ("preview", "apply", "cancel"):
        form = get_frontend_form_by_key_v1("deletion." + action)
        assert form.body_limit == 8192 and form.originating_page == DELETION_PAGE
        assert form.active_context_requirement == "deletion"
        assert form.media_type == "application/x-www-form-urlencoded"
        assert capture_safe_submitted_values_v1(form, {"confirm_delete": ["on"],
            "deletion_selection": "x" * 64}).entries == ()
        if action == "apply":
            consent, = form.safe_fields
            assert consent.field_key == "confirm_delete" and consent.cardinality == "single"
            assert consent.clear_after_rejection and consent.allowed_values == ("on",)
