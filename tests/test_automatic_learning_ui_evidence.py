"""S5 retained evidence and operation accounting; controlled Search is labelled below."""

import re
from collections import Counter
from dataclasses import replace
from html import unescape

import pytest
from test_automatic_learning_ui import create, localized_server, route_of
from test_automatic_match_evidence import genuine_candidate
from test_automatic_match_learning import rewrite, save
from test_automatic_match_learning_evidence import forbid_execution, stage
from test_match_decision_analysis import _complete_workspace
from test_match_recording_recovery_web import follow
from test_match_rollout_review import alex_workspace
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.stateful_localization import text
from skatmind.automatic_match_evidence import decode_match_source

# Imported fixture is deliberately shared, not imported test functions.
__all__ = ["localized_server"]


@pytest.fixture(scope="module")
def immediate():
    return genuine_candidate(decision=22)


def test_genuine_immediate_navigation_downloads_and_passive_accounting(
    localized_server, immediate, monkeypatch,
):
    import skatmind.app_web.automatic_match_learning as module
    import skatmind.app_web.frontend_profile_operations as profile
    import skatmind.automatic_learning_io as io
    app = localized_server.app_context
    source = decode_match_source(immediate.objects[0], immediate.source)
    save(app, workspace=source.document.workspace)
    archive = stage(app, (immediate, immediate))  # Exact duplicate is not another binding.
    native = archive.read_evidence(immediate.evidence.identity).downloads
    calls = forbid_execution(monkeypatch)
    counts = Counter()
    real_build, real_write, real_profile = (module.build_automatic_match_bundle,
                                          io.write_temporary, profile.save_frontend_profile_file_v1)
    def build(*args, **kwargs):
        counts["preparation"] += 1
        return real_build(*args, **kwargs)
    def write(directory, raw):
        counts[directory.name] += 1
        return real_write(directory, raw)
    def save_profile(*args, **kwargs):
        counts["profile"] += 1
        return real_profile(*args, **kwargs)
    monkeypatch.setattr(module, "build_automatic_match_bundle", build)
    monkeypatch.setattr(io, "write_temporary", write)
    monkeypatch.setattr(profile, "save_frontend_profile_file_v1", save_profile)
    browser = Browser(localized_server)
    browser.page("/learning")
    assert counts == {}
    page = create(browser)
    assert counts == {"preparation": 1, "generations": 1, "automatic-learning": 1}
    before = counts.copy()
    route = route_of(page)
    bundle = app.automatic_match_learning._installed.bundle
    assert len(bundle.prepared.strategy_teacher_evidence.evidences) == 1
    assert bundle.coaching.tactical_cross_game_coaching_report.focus_area_count == 0
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert text(locale, "learning.result.explanation.one_decision") in unescape(page)
        player = browser.page(route.rsplit("/", 1)[0] + "/0")
        source_page = browser.page(re.search(r'href="([^"]+/source/0)"', player)[1])
        situation = browser.page(re.search(r'href="([^"]+/situation/21)"', source_page)[1])
        assert text(locale, "automatic.knowledge") in unescape(situation)
        evidence_route = re.search(r'href="([^"]+/evidence/0)"', situation)[1]
        evidence = browser.page(evidence_route)
        assert text(locale, "saved_analysis.historical") in unescape(evidence)
        for kind, _filename, raw in native:
            assert browser.request("GET", evidence_route + "/" + kind + ".json")[2] == raw
    assert counts == before + Counter(profile=2) and calls == []
    # Live opening is explicit and requires this exact original version.
    response = browser.submit(Forms(situation).find("/learning/automatic/recording"))
    assert response[0] == 303
    assert app.managed_stateful.active_match.selected_review_decision == 22


@pytest.mark.parametrize("known", (False, True))
def test_partial_coverage_and_explicit_skips_are_distinct(localized_server, monkeypatch, known):
    app = localized_server.app_context
    save(app, workspace=alex_workspace(count=3, known_hand=known))
    calls = forbid_execution(monkeypatch)
    page = create(Browser(localized_server))
    bundle = app.automatic_match_learning._installed.bundle
    coverage = {r.name: int(r.value) for r in bundle.coverage}
    assert coverage["matches"] == coverage["observed_games"] == coverage["passed_deals"] == 1
    assert coverage["recorded_decisions"] == 3
    assert coverage["dataset_records"] == int(known)
    assert coverage["skipped_decisions"] == 3 - int(known)
    assert text("en", "automatic.count.ordinary_bindings") in unescape(page)
    assert calls == []


def test_controlled_two_game_focus_has_exact_native_support(localized_server, monkeypatch):
    """Two real producer executions with injected retained Search, NOT genuine solver proof."""
    from test_learning_corpus_tactical_coaching import _below_best_search_result
    from test_match_workspace_contracts import _definition

    import skatmind.recommendation_workflow as workflow
    monkeypatch.setattr(workflow, "solve_compatible_world_minimax", lambda **kw:
        _below_best_search_result(**kw, expected_seed=0, below_best_cards=frozenset({"C8"})))
    app = localized_server.app_context
    candidates = []
    for name in ("first", "second"):
        workspace = _complete_workspace(definition=_definition(match_id=name))
        candidates.append(genuine_candidate("bounded_search", workspace=workspace, decision=22))
        save(app, name, workspace=workspace)
    stage(app, candidates)
    calls = forbid_execution(monkeypatch)
    browser = Browser(localized_server)
    page = create(browser)
    bundle = app.automatic_match_learning._installed.bundle
    report = bundle.coaching.tactical_cross_game_coaching_report
    assert report.focus_area_count == 2
    assert all(f.qualifying_decision_count == f.distinct_game_count == 2
               for f in report.focus_areas)
    focuses = page.split('id="learning-result-primary"', 1)[1].split(
        'id="learning-result-inputs"', 1)[0]
    supports = re.findall(r'href="([^"]+/situation/[0-9]+)"', focuses)
    assert len(supports) == 4 and len(set(supports)) == 2
    from skatmind.app_web.stateful_localization import card_name
    for route in set(supports):
        situation = unescape(browser.page(route))
        assert card_name("en", "C8") in situation
        assert "game 3" in situation and "trick 8, card 1" in situation
    # The other Player has no joined Teacher evidence; another Player's focus is not theirs.
    filtered = unescape(browser.page(route_of(page).rsplit("/", 1)[0] + "/1"))
    assert text("en", "learning.result.explanation.available") not in filtered
    assert text("en", "learning.result.explanation.no_analysis") in filtered
    assert calls == []


@pytest.mark.parametrize("interrupted", (False, True))
def test_old_evidence_preview_removes_references_and_retires_dependent_result(
    localized_server, immediate, monkeypatch, interrupted,
):
    app = localized_server.app_context
    source = decode_match_source(immediate.objects[0], immediate.source)
    path, document = save(app, workspace=source.document.workspace)
    archive = stage(app, (immediate,))
    browser = Browser(localized_server)
    old_route = route_of(create(browser))
    rewrite(path, document)
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(Forms(page).find(
        "/learning/automatic/cleanup-preview", index=1)))
    assert text("en", "automatic.retire_generation") in unescape(preview)
    assert immediate.evidence.identity[:12] not in preview  # Valid typed situation caption instead.
    confirmation = Forms(preview).find("/learning/automatic/confirm")
    if interrupted:
        from pathlib import Path
        original_unlink = Path.unlink
        def unlink(path, *args, **kwargs):
            if path.parent.name == "reports" and path.suffix == ".json":
                raise OSError("Controlled deletion interruption after reference commit")
            return original_unlink(path, *args, **kwargs)
        monkeypatch.setattr(Path, "unlink", unlink)
    page = follow(browser, browser.submit(confirmation, confirm_apply="on"))
    if interrupted:
        assert text("en", "feedback.automatic_partial_cleanup") in unescape(page)
    assert archive.snapshot().manifest.evidence == ()
    assert archive.snapshot().manifest.current_generation is None
    assert browser.request("GET", old_route)[0] == 409
    assert browser.submit(confirmation, confirm_apply="on")[0] == 409
    assert path.exists()


def test_complete_and_incomplete_rollout_remain_separate(localized_server, monkeypatch):
    from test_automatic_match_rollout_evidence import executed
    from test_match_rollout_review import rollout_options

    from skatmind.automatic_match_rollout_evidence import build_match_rollout_capture_candidate
    # Two genuine bounded fixture executions; the second lacks settlement inputs.
    candidates = (build_match_rollout_capture_candidate(*executed("complete_settlement")),
        build_match_rollout_capture_candidate(*executed(options=replace(
            rollout_options("complete_settlement"), settlement_supplements={}))))
    app = localized_server.app_context
    source = decode_match_source(candidates[0].objects[0], candidates[0].source)
    save(app, workspace=source.document.workspace)
    stage(app, candidates)
    calls = forbid_execution(monkeypatch)
    browser = Browser(localized_server)
    page = create(browser)
    bundle = app.automatic_match_learning._installed.bundle
    assert bundle.debrief.report_count == len(bundle.availability) == 1
    assert bundle.prepared.strategy_teacher_evidence.source_report_count == 0
    assert bundle.coaching.tactical_cross_game_coaching_report.focus_area_count == 0
    assert text("en", "automatic.rollout_separate") in unescape(page)
    for index in (0, 1):
        evidence = browser.page(route_of(page).rsplit("/", 1)[0] + f"/evidence/{index}")
        assert text("en", "saved_analysis.historical") in unescape(evidence)
    assert calls == []


@pytest.mark.parametrize("operation", ("exclude-preview", "cleanup-preview"))
def test_maintenance_rechecks_source_during_reference_commit(
    localized_server, immediate, monkeypatch, operation,
):
    import skatmind.automatic_learning_io as io
    app = localized_server.app_context
    source = decode_match_source(immediate.objects[0], immediate.source)
    path, document = save(app, workspace=source.document.workspace)
    archive = stage(app, (immediate,))
    browser = Browser(localized_server)
    create(browser)
    if operation == "cleanup-preview":
        document = rewrite(path, document)
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(Forms(page).find(
        "/learning/automatic/" + operation, index=int(operation == "cleanup-preview"))))
    before = archive.snapshot().manifest
    original = io.write_temporary
    fired = False
    def write(directory, raw):
        nonlocal fired
        temporary = original(directory, raw)
        if directory == archive.root and not fired:
            fired = True
            rewrite(path, document, title="Concurrent saved correction")
        return temporary
    monkeypatch.setattr(io, "write_temporary", write)
    response = browser.submit(Forms(preview).find("/learning/automatic/confirm"),
                              confirm_apply="on")
    assert fired and response[0] == 409
    assert archive.snapshot().manifest == before
    assert archive.read_evidence(immediate.evidence.identity).source == source
