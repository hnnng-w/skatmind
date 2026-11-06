import re
from html import unescape
from urllib.parse import urlsplit

import pytest
from test_automatic_learning_ui import create
from test_automatic_session_review_corrections import archive_bytes, malformed_generation
from test_automatic_session_web import install_session
from test_frontend_language_switching import localized_server as _localized_server
from test_historical_game import build_historical_input
from test_session_position_export import _options, _state_for_decision
from test_session_recorded_review_web import Browser, Forms
from test_session_transitions import _apply

from skatmind.app_web.automatic_learning_controller import automatic_controller
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_profile_operations import set_frontend_language_v1
from skatmind.app_web.session_frontend import GuidedSessionContextV1
from skatmind.app_web.stateful_localization import text
from skatmind.session_commands import RecordSessionPlayCommandV1
from skatmind.session_decision_checkpoint import build_session_decision_checkpoint_v1
from skatmind.session_persistence import save_session_persistence_file_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1
from skatmind.session_position_export import export_session_position_analysis_request_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def later_session(app, *, checkpoint=True):
    data = build_historical_input()
    index = 28
    state = _state_for_decision(data, index)
    saved = build_session_decision_checkpoint_v1(state=state,
        position_export=export_session_position_analysis_request_v1(state, _options()))
    plays = [play for trick in data["tricks"] for play in trick["plays"]]
    for play in plays[index - 1:]:
        state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
            player_id=play["player_id"], card=play["card"]))
    document = build_session_persistence_document_v1(state,
        decision_checkpoints=(saved,) if checkpoint else ())
    root = app.managed_home.category("sessions").path
    active = GuidedSessionContextV1(category_root=root, path=root / "later.json",
                                    handle="a" * 64, document=document)
    save_session_persistence_file_v1(active.path, document, expected_content_fingerprint=None)
    return active, index, plays[index - 1]


@pytest.mark.parametrize("member", (None, []), ids=("null", "array"))
@pytest.mark.parametrize("locale", ("en", "de"))
def test_malformed_mixed_inventory_delivers_localized_recovery(
    localized_server, monkeypatch, member, locale,
):
    server = localized_server
    app = server.app_context
    set_frontend_language_v1(app, language=locale, expected_generation=0)
    install_session(app, missing=True)
    browser = Browser(server)
    page = create(browser)
    service = automatic_controller(app).service
    malformed_generation(service.store, member)
    before = archive_bytes(service.store)
    monkeypatch.setattr("skatmind.app_web.automatic_match_learning.build_mixed_bundle",
                        lambda *a, **kw: pytest.fail("Recovery must not prepare"))
    response = browser.submit(Forms(page).find("/learning/automatic/update"))
    assert response[0] == 400
    assert text(locale, "automatic.state.failed") in unescape(response[2].decode())
    server.app_context = AppWebContextV1.create(app.managed_home)
    fresh = Browser(server)
    status, _headers, body = fresh.request("GET", "/learning/automatic")
    print({"finding": "C-http", "member": member, "status": status})
    assert archive_bytes(service.store) == before
    assert status == 409
    assert text(locale, "automatic.state.failed") in unescape(body.decode())


@pytest.mark.parametrize("checkpoint", (True, False), ids=("eligible", "history"))
@pytest.mark.parametrize("locale", ("en", "de"))
def test_emitted_recording_action_targets_exact_later_own_play(
    localized_server, monkeypatch, checkpoint, locale,
):
    app = localized_server.app_context
    set_frontend_language_v1(app, language=locale, expected_generation=0)
    active, index, play = later_session(app, checkpoint=checkpoint)
    browser = Browser(localized_server)
    page = create(browser)
    source = browser.page(re.search(r'href="([^"]+/session/source/0)"', page)[1])
    routes = re.findall(r'href="([^"]+/session/decision/[0-9]+)"', source)
    assert len(routes) == 10  # Multiple own decisions; choose the later recorded one.
    target = browser.page(routes[-1])
    action_key = "automatic.recording" if checkpoint else "recorded_review.history"
    assert text(locale, action_key) in target
    for entry in ("skatmind.application.execute_application_invocation",
                  "skatmind.app_web.automatic_match_learning.build_mixed_bundle",
                  "skatmind.automatic_learning_io.write_temporary"):
        monkeypatch.setattr(entry, lambda *a, **kw: pytest.fail("Navigation must be read-only"))
    before = active.path.read_bytes()
    response = browser.submit(Forms(target).find("/learning/automatic/recording"))
    assert response[0] == 303
    location = response[1]["location"]
    fragment = f"recorded-decision-{index}" if checkpoint else f"session-play-{index}"
    destination = browser.page(urlsplit(location).path)
    assert f'id="{fragment}"' in destination
    tag = "p" if checkpoint else "li"
    row = re.search(r'<' + tag + r' id="' + fragment + r'"[^>]*>(.*?)</' + tag + '>',
                    destination, re.S)[1]
    player = next(p for p in active.state.players if p.player_id == play["player_id"])
    assert player.player_label in unescape(row) and play["card"] in row
    if not checkpoint:
        assert f'id="recorded-decision-{index}"' not in destination
    assert active.path.read_bytes() == before
    print({"finding": "D", "checkpoint": checkpoint, "location": location,
           "expected": fragment, "actor": play["player_id"], "card": play["card"]})
    assert location == "/sessions/current#" + fragment
