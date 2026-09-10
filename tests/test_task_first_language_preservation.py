import json

import pytest
import test_unified_local_app_web as web_helpers
from test_unified_local_app_web import (
    _bootstrap,
    _post_form,
    _request,
    _session_creation_values,
)

from skatmind.app_web.language_form_preservation import (
    apply_language_page_values_v1,
    parse_language_page_values_v1,
)

running_app_server = web_helpers.running_app_server


def _envelope(forms=(), **overrides):
    return json.dumps({"forms": list(forms), "open_disclosures": [],
                       "source_handle": None, "source_revision": None, **overrides})


def test_language_overlay_is_bounded_and_excludes_unregistered_private_values():
    raw = _envelope([{"action": "/actions/analyze/run-guided", "discriminator": {},
        "instance": 0, "values": {"hand": ["CA"], "hand_game": [],
            "fingerprint": ["private-value"], "request_file": ["private-path"]}}])
    state = parse_language_page_values_v1(raw, route="/analyze")
    values = state.forms[0].safe_values
    assert values.all("hand") == ("CA",)
    assert values.all("hand_game") == ("",)
    assert not values.contains("fingerprint") and not values.contains("request_file")
    html = ('<form action="/actions/analyze/run-guided"><input type="checkbox" '
            'name="hand_game" checked><input type="checkbox" name="hand" value="CA"></form>')
    rendered = apply_language_page_values_v1(html, state)
    assert 'name="hand_game" checked' not in rendered
    assert 'value="CA" checked="checked"' in rendered
    with pytest.raises(ValueError):
        parse_language_page_values_v1(" " * 262145, route="/analyze")
    with pytest.raises(ValueError):
        parse_language_page_values_v1('{"forms": [], "forms": []}', route="/analyze")


def test_explicit_language_post_preserves_card_without_command_or_identity_generation(
    running_app_server, monkeypatch,
):
    server = running_app_server
    cookie, headers = _bootstrap(server)
    assert _post_form(server, "/sessions/create", headers,
        _session_creation_values(server, game_name="Switch test"))[0] == 303
    active = server.app_context.managed_stateful.active_session
    original = active.document
    import skatmind.app_web.server as server_module
    monkeypatch.setattr(server_module.secrets, "token_bytes",
                        lambda *args: pytest.fail("Language switching generated an identity"))
    raw = _envelope([{"action": "/sessions/command", "discriminator": {"kind": "record_dealt_card"},
        "instance": 0, "values": {"card": ["CA"]}}], source_handle=active.handle,
        source_revision="0", open_disclosures=[0])
    status, response_headers, _body = _post_form(server, "/actions/profile/language", headers, {
        "language": "de", "return_to": "/sessions/current",
        "profile_generation": str(server.app_context.frontend_profile.generation),
        "_frontend_language_values": raw,
    })
    assert status == 303 and response_headers["location"] == "/sessions/current"
    status, _headers, body = _request(
        server, "GET", "/sessions/current", headers={"Cookie": cookie})
    assert status == 200 and b'<html lang="de">' in body
    assert b'value="CA" selected' in body
    assert active.document is original and active.execution is None
    assert server.app_context.language_page_values is None


def test_stale_language_form_cannot_change_profile_or_active_product(running_app_server):
    server = running_app_server
    _cookie, headers = _bootstrap(server)
    assert _post_form(server, "/sessions/create", headers,
        _session_creation_values(server, game_name="Stale switch"))[0] == 303
    original = server.app_context.frontend_profile
    active = server.app_context.managed_stateful.active_session
    status, _headers, _body = _post_form(server, "/actions/profile/language", headers, {
        "language": "de", "return_to": "/sessions/current",
        "profile_generation": str(original.generation),
        "_frontend_language_values": _envelope(source_handle="0" * 64, source_revision="0"),
    })
    assert status == 409
    assert server.app_context.frontend_profile is original
    assert active.state.revision == 0
