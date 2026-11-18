"""Source-only #326 probe; genuine disposable fixtures, no installed/UAT data."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import shutil
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import pytest  # noqa: E402
from learning_archive_fixture_helpers import measure_work, publish_fresh_archive  # noqa: E402
from test_automatic_historical_evidence import genuine_historical  # noqa: E402
from test_automatic_historical_web import source_link  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_historical_review_form import _completed_example_draft  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_match_rollout_web import open_alex  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402
from whole_game_review_fixtures import ten_decision_document  # noqa: E402

from skatmind.app_web.historical_form import update_historical_options_v1  # noqa: E402
from skatmind.app_web.saved_match_analyses import archive_store  # noqa: E402
from skatmind.automatic_historical_evidence import build_historical_capture_candidate  # noqa: E402
from skatmind.session_history import build_session_state_from_accepted_prefix_v1  # noqa: E402


@contextmanager
def observed(store, name, results):
    """Inclusive named timings (nested, not additive) plus real archive work counts."""
    with pytest.MonkeyPatch.context() as patch:
        counts = measure_work(patch, store)
        times, calls = Counter(), Counter()
        targets = {
            "build_historical_game_review_summary": "engine_historical_immediate",
            "recommend_card_by_expected_value": "engine_immediate",
            "execute_whole_game_rollout_v1": "engine_rollout",
            "build_hidden_card_inference_model": "inference_model",
            "generate_sampled_hidden_state": "sampling",
            "serialize_result": "serialization",
            "validate_output_document": "output_validation",
            "retain_manual_review": "retention",
            "capture_match_inventory": "inventory",
            "capture_mixed_inventory": "inventory",
            "capture_manual_delivery": "manual_delivery_capture",
            "build_historical_request_v1": "source_preparation",
            "prepare_match_decision_v1": "source_preparation",
        }
        originals = {}
        for module in tuple(sys.modules.values()):
            if module is None or not getattr(module, "__name__", "").startswith("skatmind"):
                continue
            for attr, value in tuple(vars(module).items()):
                if attr in targets and callable(value):
                    originals.setdefault(id(value), (value, targets[attr], []))[2].append(
                        (module, attr))
        def wrapper(original, label):
            def run(*args, **kwargs):
                start = perf_counter()
                calls[label] += 1
                try:
                    return original(*args, **kwargs)
                finally:
                    times[label] += perf_counter() - start
            return run
        for original, label, aliases in originals.values():
            wrapped = wrapper(original, label)
            for module, attr in aliases:
                patch.setattr(module, attr, wrapped)
        from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
        from skatmind.app_web.historical_review_retention import ManualReviewDelivery
        from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1
        from skatmind.automatic_learning_store import AutomaticLearningStoreV1
        for owner, attr, label in (
            (AutomaticLearningStoreV1, "_admission", "admission"),
            (AutomaticLearningStoreV1, "_snapshot_for_delivery", "archive_delivery"),
            (AutomaticMatchLearningServiceV1, "validate_final_delivery", "final_automatic"),
            (ManualReviewDelivery, "validate", "manual_validation"),
            (SkatMindAppWebRequestHandlerV1, "_send_bytes", "final_http"),
        ):
            patch.setattr(owner, attr, wrapper(getattr(owner, attr), label))
        start = perf_counter()
        yield
        row = {"name": name, "seconds": perf_counter() - start, "work": dict(counts),
               "inclusive_seconds": dict(times), "calls": dict(calls)}
        results.append(row)
        print(json.dumps(row), flush=True)


def saved_sequence(browser, store, results, suffix):
    for temperature in ("cold", "warm"):
        with observed(store, f"list_{suffix}_{temperature}", results):
            page = browser.page("/review/saved")
    with observed(store, "source_open_" + suffix, results):
        source = browser.page(source_link(page))
    with observed(store, "reopen_post_" + suffix, results):
        response = browser.submit(Forms(source).find("/review/reopen"))
        assert response[0] == 303
    with observed(store, "reopen_redirect_get_" + suffix, results):
        follow(browser, response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--create-fixtures", action="store_true")
    parser.add_argument("--counts", nargs="+", type=int, default=(2, 33))
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    results = []
    if args.create_fixtures:
        assert args.fixtures.parent.is_dir() and not args.fixtures.exists()
        args.fixtures.mkdir()
        start = perf_counter()
        genuine = genuine_historical.__wrapped__()
        for count in (2, 33):
            folder = args.fixtures / str(count)
            fixture = localized_server.__wrapped__(folder)
            server = next(fixture)
            try:
                store = archive_store(server.app_context, initialize=True)
                candidates = tuple(build_historical_capture_candidate(f"synthetic-{i:02}", 0,
                    genuine[1], genuine[2], draft=genuine[0]) for i in range(count))
                publish_fresh_archive(store, store.snapshot(), candidates, live_historical=True)
            finally:
                fixture.close()
        results.append({"name": "fixture_construction", "seconds": perf_counter() - start,
                        "genuine_executions": 1})
    original_connection = http.client.HTTPConnection
    class ProbeConnection(original_connection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **{**kwargs, "timeout": 7200})
    http.client.HTTPConnection = ProbeConnection
    for count in args.counts:
        folder = args.output / str(count)
        shutil.copytree(args.fixtures / str(count), folder)
        fixture = localized_server.__wrapped__(folder)
        server = next(fixture)
        try:
            app = server.app_context
            store = archive_store(app)
            snapshot, receipt = store._snapshot_for_delivery()
            results.append({"name": "archive_" + str(count),
                "objects": len(snapshot.manifest.objects), "stored_bytes": snapshot.retained_bytes,
                "available": len(snapshot.available_evidence_ids),
                "receipt": receipt is not None,
                "fallback": None if receipt is not None else "object_count_above_64"})
            browser = Browser(server)
            saved_sequence(browser, store, results, str(count) + "_before")
            if count == 2:
                # Native completion of the genuine full thirty-Play guided game.
                app.review_state = app.review_state.mutate(
                    expected_revision=app.review_state.revision,
                    draft=update_historical_options_v1(_completed_example_draft(),
                        immediate_review=True, immediate_sample_count=25,
                        immediate_base_random_seed=11))
                page = browser.page("/review")
                with observed(store, "guided_quick_post", results):
                    response = browser.submit(Forms(page).find("/actions/review/run-guided"))
                    assert response[0] == 303 and app.historical_reviews.notice[1] == "saved"
                with observed(store, "guided_quick_redirect_get", results):
                    follow(browser, response)
                for kind in ("request", "result"):
                    raw = getattr(app.review_state, kind + "_json_bytes")
                    (args.output / ("guided-" + kind + ".json")).write_bytes(raw)
                    results.append({"name": "guided_" + kind, "bytes": len(raw),
                                    "sha256": hashlib.sha256(raw).hexdigest()})
                saved_sequence(browser, store, results, "2_after")
                browser, _path, page = open_alex(server, count=30)
                page = follow(browser, browser.submit(Forms(page).find("/matches/select-decision"),
                                                     decision_index="25"))
                with observed(store, "match_quick_rollout_post", results):
                    response = browser.submit(Forms(page).find("/matches/review-whole-game"),
                        analysis_effort="quick", objective="played_game_goal")
                    assert response[0] == 303
                with observed(store, "match_quick_rollout_redirect_get", results):
                    page = follow(browser, response)
                with observed(store, "match_quick_immediate_post", results):
                    response = browser.submit(operation_form(page, "analyze_decision"),
                                              analysis_effort="quick")
                    assert response[0] == 303
                with observed(store, "match_quick_immediate_redirect_get", results):
                    follow(browser, response)
                import skatmind.api.v1.session as session_api
                from skatmind.app_web.session_frontend import import_guided_session_v1
                document = ten_decision_document(bid_value=18)
                checkpoint = document.decision_checkpoints[-1]
                prefix = build_session_state_from_accepted_prefix_v1(document.state,
                    target_revision=checkpoint.source_revision)
                active = import_guided_session_v1(app.managed_stateful.root("sessions"),
                    handle="a" * 64,
                    document=session_api.build_session_persistence_document(prefix).value.to_dict())
                app.managed_stateful.activate_session(active)
                native = Forms(browser.page()).find("/sessions/analyze")
                with observed(store, "session_current_quick_post", results):
                    response = browser.submit(native, analysis_effort="quick")
                    assert response[0] in (200, 303)
                    if response[0] == 200:
                        assert b'id="forced-card-guidance"' in response[2]
                if response[0] == 303:
                    with observed(store, "session_current_quick_redirect_get", results):
                        follow(browser, response)
        finally:
            fixture.close()
            (args.output / "report.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
