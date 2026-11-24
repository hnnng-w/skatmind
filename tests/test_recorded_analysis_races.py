"""Force real publication boundaries without sleeps, clock deadlines or speculative work."""

import json
import re
from contextlib import contextmanager
from threading import Event
from unittest.mock import patch

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_rollout_web import open_alex
from test_session_recorded_review_web import Browser, Forms, record_live_game

import skatmind.recommendation_workflow as workflow
from skatmind.app_web import session_batch_routes, whole_match_routes


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


@contextmanager
def interleaved_run(server, family):
    """Shared HTTP and real-browser fixture: only explicit POSTs initiate work."""
    app = server.app_context
    session = family == "sessions"
    page = (session_batch_routes if session else whole_match_routes).PAGE
    if session:
        client = Browser(server)
        record_live_game(client, play_count=6)
        path, owner = app.managed_stateful.active_session.path, app.session_batch
    else:
        client, path, _ = open_alex(server)
        owner = app.whole_match
    original = path.read_bytes()
    calls, conflicts = [], []
    blocked, release = Event(), Event()
    evaluate = workflow.evaluate_whole_game_rollout_v1

    def controlled(*args, **kwargs):
        calls.append(len(calls) + 1)
        if len(calls) == 2:
            blocked.set()
            assert release.wait(120)
        elif not session:
            ticks = iter(range(0, 1000000, 100))
            kwargs["clock"] = lambda: next(ticks)
        return evaluate(*args, **kwargs)

    def finish():
        if worker := owner.worker:
            worker.thread.join(120)
        assert owner.worker is None

    handler = server.RequestHandlerClass
    send = handler._send_bytes

    def send_after_publication(self, status, content, **kwargs):
        if self.path.endswith("/results") and session:
            if status == 200 and not release.is_set():
                # The first comparison has its manifest and original final guard.
                release.set()
                finish()
            if status == 409:
                conflicts.append(self.path)
        return send(self, status, content, **kwargs)

    with (patch.object(workflow, "evaluate_whole_game_rollout_v1", controlled),
          patch.object(handler, "_send_bytes", send_after_publication)):
        try:
            start = Forms(client.page(page)).find(page + "/start")
            response = client.submit(start, analysis_effort="quick", objective="played_game_goal")
            assert response[0] == 303
            if not session:
                finish()
                resume = Forms(client.page(page)).find(page + "/resume")
                assert client.submit(resume)[0] == 303
            assert blocked.wait(120)
            watch = re.search(r'data-batch-watch="([^"]+)"', client.page(page))[1]
            yield client, page, watch, release, finish, conflicts
        finally:
            release.set()
            finish()
        assert calls == [1, 2] and original == path.read_bytes()


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_pinned_projection_rejects_race_and_delivers_exact_new_receipt(localized_server, family):
    with interleaved_run(localized_server, family) as run:
        client, page, watch, release, finish, errors = run
        first = json.loads(client.page(watch + "/status"))
        assert (first["phase"], first["processed"]) == ("working", 1)
        status, headers, raw = client.request("GET", watch + "/results")
        if family == "sessions":
            assert status == 409 and errors == [watch + "/results"]
            assert b"/from-game/" not in raw
        else:
            assert status == 200 and headers["x-result-revision"] == first["revision"]
            assert b"/25)" in raw and b"84%" not in raw
            release.set()
            finish()
        latest = json.loads(client.page(watch + "/status"))
        assert (latest["phase"], latest["processed"]) == ("finished", 2 if errors else 1)
        assert latest["revision"] != first["revision"]
        status, headers, raw = client.request("GET", watch + "/results")
        assert status == 200 and headers["x-result-revision"] == latest["revision"]
        assert raw.count(b"/from-game/") == 2 if errors else b"84%" in raw
        # Only this explicit Resume supersedes the run. The old watch cannot follow it.
        resume = Forms(client.page(page)).find(page + "/resume")
        assert client.submit(resume)[0] == 303
        finish()
        for part in ("status", "results"):
            assert client.request("GET", watch + "/" + part)[0] == 409
