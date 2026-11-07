"""Genuine managed Historical publisher, original materialization and one-Game coverage."""

import pytest
from test_match_evidence_retention import managed

from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.match_frontend import execute_unified_match_analysis_v1
from skatmind.app_web.saved_match_analyses import archive_store

__all__ = ["managed"]


@pytest.mark.parametrize("review", (False, True))
def test_managed_historical_publication_retains_exact_workspace_without_duplicate_game(
    managed, review, monkeypatch,
):
    import skatmind.automatic_match_historical_evidence as adapter
    original_builder = adapter.build_match_historical_capture_candidate
    def checked(*args, **kwargs):
        try:
            return original_builder(*args, **kwargs)
        except Exception as error:
            raise AssertionError("Genuine Match Historical admission failed") from error
    monkeypatch.setattr(adapter, "build_match_historical_capture_candidate", checked)
    app, active = managed
    before = active.path.read_bytes()
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    original = service._installed.bundle.downloads
    result = execute_unified_match_analysis_v1(active, {
        "operation": "analyze_historical_game", "match_position": "3",
        "expected_revision": str(active.workspace.revision),
        "decision_snapshots": "true",
        "immediate_review": str(review).lower(), "immediate_sample_count": "1",
    }, app_context=app)
    assert result.status == "applied"
    assert active.evidence_notice[1] == "saved"
    store = archive_store(app)
    manifest = store.snapshot().manifest
    assert manifest.historical_heads == ()
    entry, = manifest.evidence
    retained = store.read_evidence(entry.identity)
    assert retained.report.report_kind == "historical_analysis"
    assert retained.source.document.workspace == active.workspace
    assert service.update().status == "prepared"
    assert service._installed.bundle.downloads == original
    assert service._installed.bundle.evidence == ()
    assert len(service._installed.bundle.historical_evidence) == 1
    assert len(service._installed.bundle.sources) == 1
    assert service._installed.bundle.historical_sources == ()
    assert active.path.read_bytes() == before
    if not review:
        # Controlled rehashed Report contradiction: preserve the original invocation,
        # Result and Workspace, but replace its claimed materialized Request.
        from dataclasses import replace

        from test_automatic_match_evidence import commit_candidate
        from test_automatic_match_learning_evidence import forbid_execution

        from skatmind.api.v1 import parse_request
        from skatmind.automatic_historical_codec import pack_native
        from skatmind.automatic_learning_codec import canonical_json, decode_json
        from skatmind.automatic_learning_store import resume_automatic_learning_store_v1
        from skatmind.automatic_match_evidence import _download_record
        from skatmind.automatic_session_evidence import SessionCaptureCandidate
        from skatmind.match_analysis_contracts import build_match_analysis_report_v1

        forbid_execution(monkeypatch)
        root = retained.report.value.request.to_dict()["document"]
        root["historical_game_input"]["players"][0]["player_label"] = (
            "Contradictory materialization")
        changed = build_match_analysis_report_v1(replace(retained.report.value,
                                                        request=parse_request(root)))
        obj = store.read_object(entry.envelope)
        data = decode_json(obj.payload)
        data["report"] = pack_native(changed)
        data["downloads"] = [_download_record(*row) for row in adapter._downloads(changed)]
        obj = replace(obj, payload=canonical_json(data))
        bad = replace(entry, envelope=obj.reference)
        with pytest.raises(ValueError, match="materialization"):
            adapter.decode_match_historical_execution(obj, bad, retained.source)
        commit_candidate(store, SessionCaptureCandidate(retained.source.record, bad,
            (store.read_object(retained.source.record.object_ref), obj)))
        resumed = resume_automatic_learning_store_v1(store.root).snapshot()
        assert bad.identity not in resumed.available_evidence_ids
        assert entry.identity in resumed.available_evidence_ids
