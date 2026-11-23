"""Issue #332: generate a disposable import and measure one genuine Quick review."""

import argparse
import json
import random
import re
import shutil
import sys
import time
from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from test_historical_game import build_historical_input  # noqa: E402
from test_match_workspace_contracts import (  # noqa: E402
    _definition,
    _observed_game,
    _seat_order,
    _set_game,
    declaration_from_historical,
    observed_plays_from_historical,
)

from skatmind.deck import get_full_deck  # noqa: E402
from skatmind.match_workspace_contracts import create_match_workspace_v1  # noqa: E402
from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1  # noqa: E402
from skatmind.match_workspace_persistence import save_match_workspace_file_v1  # noqa: E402
from skatmind.match_workspace_persistence_codec import (  # noqa: E402
    build_match_workspace_persistence_document_v1,
)


def synthetic_game(definition, p):
    deck = get_full_deck()
    random.Random(33200 + p).shuffle(deck)
    data = build_historical_input(game_type=("null" if p == 33 else
        "grand" if p % 2 else "hearts"), hand_game=True, deck=deck)
    seats = _seat_order(definition, p)
    ids = dict(zip(("player-a", "player-b", "player-c"), seats, strict=True))
    hand = next(row["initial_hand"] for row in data["players"]
                if ids[row["player_id"]] == definition.perspective_player_id)
    return _observed_game(definition, match_position=p, declaration=declaration_from_historical(
        data), declarer_player_id=ids[data["declarer_player_id"]],
        perspective_initial_hand=None if p == 34 else hand,
        plays=tuple(replace(play, player_id=ids[play.player_id])
            for play in observed_plays_from_historical(data, count=30 if p <= 7 else 3)))


def synthetic():
    definition = _definition(match_id="synthetic-332", title="Synthetic mixed 36-game recording",
                             perspective_player_id="player-a")
    workspace = create_match_workspace_v1(definition)
    for p in range(1, 36):
        if p == 35:
            workspace = mark_match_workspace_passed_deal_v1(workspace, match_position=p,
                expected_revision=workspace.revision, game_timecode=None).workspace
            continue
        workspace = _set_game(workspace, synthetic_game(definition, p))
    return build_match_workspace_persistence_document_v1(workspace)


def measure(output, document, earlier=None):
    import http.client

    from test_frontend_language_switching import localized_server
    from test_recorded_review_navigation import chooser_form, home_chooser
    from test_session_recorded_review_web import Browser

    import skatmind.application.execution as executor
    import skatmind.automatic_learning_io as io
    import skatmind.automatic_match_rollout_evidence as codec
    import skatmind.recommendation_workflow as workflow
    from skatmind.app_web import whole_match_job as jobs
    from skatmind.app_web.whole_match_plan import own_plays
    from skatmind.app_web.whole_match_routes import OVERVIEW
    from skatmind.app_web.whole_match_web import configuration
    from skatmind.automatic_learning_store import AutomaticLearningStoreV1 as Store

    counts, seconds, outcomes = Counter(), Counter(), Counter()
    report = {"python": sys.version, "phases": {}, "outcomes": outcomes}
    def instrument(module, name):
        real = getattr(module, name)
        def timed(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = real(*args, **kwargs)
                if name == "evaluate_whole_game_rollout_v1":
                    outcomes[result.status] += 1
                    outcomes["tied_best"] += len(result.tied_best_cards) > 1
                    outcomes["completed_common_worlds"] += result.completed_common_worlds
                    outcomes["card_transitions"] += result.work.card_transitions
                    outcomes["terminal_evaluations"] += result.work.terminal_evaluations
                if name == "read_bounded" and args[0].parent.name in ("sources", "reports"):
                    counts["object_reads"] += 1
                    counts["object_bytes"] += len(result)
                return result
            finally:
                counts[name] += 1
                seconds[name] += time.perf_counter() - start
        return patch.object(module, name, timed)

    def phase(name, start):
        report["phases"][name] = {"wall": time.perf_counter()-start,
                                  "counts": dict(counts), "inclusive_seconds": dict(seconds)}
        (output / "measurement.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        counts.clear()
        seconds.clear()

    with ExitStack() as stack:
        for mod, name in ((executor, "execute_application_invocation"),
                (workflow, "evaluate_whole_game_rollout_v1"), (Store, "_admission"),
                (codec, "decode_match_rollout"), (Store, "_validate_update"),
                (io, "read_bounded"), (jobs, "build_match_rollout_capture_candidate")):
            stack.enter_context(instrument(mod, name))
        fixture = localized_server.__wrapped__(output)
        server = next(fixture)
        stack.callback(fixture.close)
        app = server.app_context
        if earlier is not None:
            # Build a disposable above-limit starting point from the first probe.
            # Keep all immutable bytes; only this copy omits the last Report index.
            from skatmind.app_web.saved_match_analyses import archive_store

            assert earlier != output and (earlier / "measurement.json").is_file()
            assert (earlier / "synthetic-332.json").read_bytes() == (
                output / "synthetic-332.json").read_bytes()
            shutil.copytree(earlier / "managed" / "automatic-learning",
                            app.managed_home.root / "automatic-learning")
            seed = archive_store(app)
            before = seed._manifest()
            assert len(before.evidence) == 62
            omitted = before.evidence[-1]
            subset = replace(before, revision=before.revision + 1, evidence=before.evidence[:-1],
                objects=tuple(e for e in before.objects if e.reference != omitted.envelope))
            result = seed.update_manifest(subset, expected_manifest=before.fingerprint)
            assert result.status == "saved"
        path = app.managed_stateful.root("matches") / "synthetic-332.json"
        assert save_match_workspace_file_v1(path, document,
                                            expected_content_fingerprint=None).status == "saved"
        browser = Browser(server)
        assert browser.submit(chooser_form(home_chooser(browser), "matches"))[0] == 303
        active = app.managed_stateful.active_match
        rows = own_plays(active.workspace)
        report["inventory"] = dict(Counter(row.reason or "eligible" for row in rows))
        cfg = configuration({"analysis_effort": "quick", "objective": "played_game_goal",
            "random_seed": "0"}, active.workspace, rows)
        counts.clear()
        seconds.clear()
        start = time.perf_counter()
        with app.whole_match.lock:
            jobs.control(app, active, "start", jobs.proof(active, None), configuration=cfg)
            worker = app.whole_match.worker
        worker.thread.join()
        state = jobs.progress_file(app, active).read()
        report["phase"], report["settings"] = state["phase"], state["settings"]
        report["refs"] = dict(Counter(ref[0] for ref in state["refs"].values()))
        store = app.saved_match_analyses.store
        report["objects"] = len(store._manifest().objects)
        report["object_bytes"] = sum(e.reference.size_bytes for e in store._manifest().objects)
        report["progress_bytes"] = jobs.progress_file(app, active).path.stat().st_size
        phase("start_to_worker_exit", start)
        assert state["phase"] == "finished"
        if earlier:
            assert report["refs"] == {"computed": 1, "reused": 61}
            assert report["phases"]["start_to_worker_exit"]["counts"][
                "execute_application_invocation"] == 1

        def get(route):
            conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=3600)
            try:
                conn.request("GET", route, headers={"Cookie": browser.cookie})
                response = conn.getresponse()
                raw = response.read()
                assert response.status == 200, response.status
                return raw.decode()
            finally:
                conn.close()
        start = time.perf_counter()
        html = get(OVERVIEW)
        phase("reopen_overview", start)
        detail = re.search(r'href="(/matches/saved-analyses/[^"]+/from-review/[^"]+)"', html)[1]
        start = time.perf_counter()
        assert detail.split("/from-review/")[0] + "/request.json" in get(detail)
        phase("open_original_detail", start)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--retained-from", type=Path, help="Earlier synthetic verification output")
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    doc = synthetic()
    assert save_match_workspace_file_v1(args.output / "synthetic-332.json", doc,
                                        expected_content_fingerprint=None).status == "saved"
    if args.measure:
        measure(args.output, doc, args.retained_from)
