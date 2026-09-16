"""Optional installed-Wheel native Learning evidence in disposable synthetic homes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import replace
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from _workflow_visual_browser import LocalBrowser
from verify_local_time_entry import native_select
from verify_match_format_presentation import native_text
from verify_recording_deletion import focus, measure, submit

import skatmind
import skatmind.app_web.learning_direct_entry as direct
import skatmind.app_web.server as web
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.stateful_context import ManagedStatefulContextV1
from skatmind.match_workspace_contracts import _build_match_workspace_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "localization-test-token"
ADD = 'form[action="/learning/add-recorded-match"]'
BUILD = '#learning-build form > button'
MODULES = ("learning_direct_entry.py", "learning_direct_entry_http.py", "learning_frontend.py",
    "task_first_learning_rendering.py", "task_first_projections.py", "stateful_context.py",
    "form_registry.py", "server.py", "language_context.py", "language_form_preservation.py",
    "recording_deletion.py", "assets/app.css", "assets/workflow.js",
    "locales/de.json", "locales/en.json")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def choose_source(cdp, handle, evidence):
    selector = ADD + ' [name="source_handle"]'
    index = cdp.evaluate(f"[...document.querySelector('{selector}').options]"
                         f".findIndex(o=>o.value==={json.dumps(handle)})")
    assert index > 0
    cdp.events.clear()
    assert native_select(cdp, selector, down=index) == handle
    assert not [e for e in cdp.events if e["params"]["request"]["method"] == "POST"]
    evidence["actions"].append({"name": "choose-source", "posts": [], "focus": focus(cdp)})
    assert focus(cdp)["visible"]


def flow(cdp, server, output, evidence, counts):
    # Existing legal fixtures only establish saved sources. All Add, Build, version
    # selection, conflict resolution and language actions below are native keyboard.
    from test_learning_direct_entry_web import downloads, independent_workspace, source_handle
    from test_match_recording_recovery_web import entry_action, follow, operation_form
    from test_recorded_review_navigation import chooser_form, external_pass, saved_partial_match
    from test_session_recorded_review_web import Browser
    browser = Browser(server)
    path, workspace = saved_partial_match(server)
    follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
    active = server.app_context.managed_stateful.active_match
    follow(browser, browser.submit(operation_form(browser.page("/matches/position/3"),
        "analyze_decision"), immediate_sample_count="2"))
    report = active.capture.report_store.list()[0]
    assert report.value.status == "executed"
    follow(browser, browser.submit(entry_action(
        browser.page("/matches/position/3"), 2, rewind=True)))
    recovery = (active.recovery.selected, active.recovery.preview)
    source = independent_workspace(workspace, "inactive-browser-source")
    source = _build_match_workspace_v1(match_definition=replace(source.match_definition,
        title="Synthetic same title " + "LongName" * 16),
        revision=source.revision, slots=source.slots)
    source_path = path.with_name("inactive.json")
    assert save_match_workspace_file_v1(source_path,
        build_match_workspace_persistence_document_v1(source),
        expected_content_fingerprint=None).status == "saved"
    evidence["fixture_setup"] = [
        "Strictly saved six-Play partial Match; independent inactive Match",
        "Explicit HTTP open of other Match, Game 3, genuine two-sample Report and recovery"]
    evidence["source_identity"] = source.match_definition.match_id
    evidence["active_identity"] = active.workspace.match_definition.match_id
    original = path.read_bytes(), source_path.read_bytes()
    cdp.navigate(server.origin + "/learning")
    submit(cdp, f'.language-selector button[value="{evidence["locale"]}"]', evidence,
           "initial-language")
    create = 'form[action="/learning/create"]'
    native_text(cdp, create + ' [name="collection_name"]', "Synthetic native Learning")
    submit(cdp, create + ' button', evidence, "create-collection")
    assert cdp.evaluate("location.pathname") == "/learning/current"
    target = server.app_context.managed_stateful.active_learning
    submit(cdp, 'a[href="/learning/recorded-matches/refresh"]', evidence, "refresh",
           expected_posts=0)
    measure(cdp, output, evidence, "choose", "#learning-recorded-matches")
    measure(cdp, output, evidence, "choose-controls", ADD)
    assert cdp.evaluate(f"document.querySelector('{ADD} [name=source_handle]').value") == ""
    profile = server.app_context.frontend_profile.profile_path.read_bytes()
    choose_source(cdp, source_handle(source_path), evidence)
    assert counts["import"] == counts["build"] == 0
    # #223: browser-only unsent selection is preserved only with the enhancement.
    for locale in ("en" if evidence["locale"] == "de" else "de", evidence["locale"]):
        submit(cdp, f'.language-selector button[value="{locale}"]', evidence,
               "unsent-choice-language-" + locale)
        chosen = cdp.evaluate(f"document.querySelector('{ADD} [name=source_handle]').value")
        assert chosen == (source_handle(source_path) if evidence["javascript"] else "")
        assert counts["import"] == counts["build"] == 0
    if not evidence["javascript"]:
        choose_source(cdp, source_handle(source_path), evidence)
    profile = server.app_context.frontend_profile.profile_path.read_bytes()
    submit(cdp, ADD + ' > button', evidence, "add-inactive")
    assert counts["import"] == 1 and counts["build"] == 0
    assert cdp.evaluate("location.pathname+location.hash") == direct.LEARNING_ENTRY_LOCATION
    assert target.corpus.store.match_snapshots[0].workspace == source
    assert target.corpus.prepared_artifacts is None
    assert server.app_context.managed_stateful.active_match is active
    measure(cdp, output, evidence, "added", "#learning-recorded-matches")
    measure(cdp, output, evidence, "build-controls", "#learning-build form")
    submit(cdp, BUILD, evidence, "build")
    assert counts["build"] == 1
    prepared = target.corpus.prepared_artifacts
    data = prepared.learning_dataset
    evidence["coverage"] = {"observed": data.observed_decision_count,
        "usable": data.record_count, "skipped": data.skipped_decision_count,
        "status": data.status, "teacher": data.strategy_teacher_evidence_count}
    assert evidence["coverage"] == dict(
        observed=6, usable=2, skipped=4, status="partial", teacher=0)
    submit(cdp, 'a.button-link[href="#learning-results"]', evidence, "view-results",
           expected_posts=0)
    assert cdp.evaluate("location.hash") == "#learning-results"
    assert cdp.evaluate("document.activeElement.id") == "learning-results"
    measure(cdp, output, evidence, "results", "#learning-results")
    retained = downloads(browser)
    evidence["downloads"] = {kind: {"filename": filename, "sha256": digest(content)}
                             for kind, (filename, content) in retained.items()}
    # Native authenticated download link too; canonical bytes are checked by real HTTP.
    submit(cdp, '#learning-results a[download]', evidence, "download", expected_posts=0)
    assert counts["import"] == counts["build"] == 1
    assert server.app_context.frontend_profile.profile_path.read_bytes() == profile
    for locale in ("en" if evidence["locale"] == "de" else "de", evidence["locale"]):
        submit(cdp, f'.language-selector button[value="{locale}"]', evidence, "language-" + locale)
        assert cdp.evaluate("location.pathname") == "/learning/current"
    assert target.corpus.prepared_artifacts is prepared and downloads(browser) == retained
    cdp.navigate(server.origin + "/learning/current")
    choose_source(cdp, source_handle(source_path), evidence)
    submit(cdp, ADD + ' > button', evidence, "identical")
    assert target.last_result.status == "unchanged"
    assert target.corpus.prepared_artifacts is prepared and downloads(browser) == retained
    prior = target.corpus.store.document.catalog.current_matches
    revised = external_pass(source_path, source)
    evidence["fixture_setup"].append("External real saved source update: one passed position")
    choose_source(cdp, source_handle(source_path), evidence)
    submit(cdp, ADD + ' > button', evidence, "add-updated-saved-version")
    assert target.corpus.store.document.catalog.current_matches == prior
    assert target.corpus.prepared_artifacts is None
    select = 'form:has(input[value="select_current_snapshot"])'
    # Open the actual native disclosure through its summary; no DOM form submission.
    cdp.activate('#insight-versions details > summary')
    measure(cdp, output, evidence, "retained-versions", "#insight-versions")
    submit(cdp, select + ' button', evidence, "select-retained-version")
    assert target.corpus.store.document.catalog.current_matches != prior
    submit(cdp, BUILD, evidence, "rebuild-selected-version")
    assert counts["build"] == 2
    conflict = _build_match_workspace_v1(match_definition=replace(revised.match_definition,
        title="Same revision, independent saved contents"), revision=revised.revision,
        slots=revised.slots)
    assert save_match_workspace_file_v1(source_path,
        build_match_workspace_persistence_document_v1(conflict),
        expected_content_fingerprint=build_match_workspace_persistence_document_v1(
            revised).content_fingerprint).status == "saved"
    evidence["fixture_setup"].append("Real same-revision changed-title source file for conflict")
    choose_source(cdp, source_handle(source_path), evidence)
    submit(cdp, ADD + ' > button', evidence, "same-revision-conflict")
    assert target.last_result.status == "resolution_required"
    assert counts["import"] == 4
    assert cdp.evaluate(f"document.querySelector('{ADD} details').open")
    for locale in ("en" if evidence["locale"] == "de" else "de", evidence["locale"]):
        submit(cdp, f'.language-selector button[value="{locale}"]', evidence,
               "submitted-conflict-language-" + locale)
        assert cdp.evaluate(f"document.querySelector('{ADD} [name=source_handle]').value") == (
            source_handle(source_path))
        assert counts["import"] == 4
    measure(cdp, output, evidence, "conflict", "#learning-recorded-matches")
    measure(cdp, output, evidence, "conflict-controls", ADD)
    assert native_select(cdp, ADD + ' [name=same_revision_resolution]', down=1) == "retain"
    submit(cdp, ADD + ' > button', evidence, "explicit-retain")
    assert counts["import"] == 5 and target.last_result.status == "applied"
    submit(cdp, BUILD, evidence, "explicit-rebuild-after-retain")
    measure(cdp, output, evidence, "final-results", "#learning-results")
    assert counts["build"] == 3 and counts["activation"] == 1  # Only fixture opening.
    assert active.capture.report_store.list() == (report,)
    assert active.selected_position == 3
    assert (active.recovery.selected, active.recovery.preview) == recovery
    assert path.read_bytes() == original[0]
    assert server.app_context.managed_stateful.active_match is active
    evidence["no_source_activation"] = True
    evidence["counts"] = dict(counts)
    evidence["source_original_sha256"] = digest(original[1])
    evidence["other_recording_sha256"] = digest(original[0])


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh external scratch directory.")
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    hashes = {}
    for name in MODULES:
        raw = files("skatmind.app_web").joinpath(name).read_bytes()
        assert raw == (ROOT / "src/skatmind/app_web" / name).read_bytes(), name
        hashes[name] = digest(raw)
    # Legal test fixtures do not install or select Product code from the repository.
    sys.path.insert(0, str(ROOT / "tests"))
    sys.path.insert(0, str(ROOT))
    output.mkdir()
    evidence = {"completed": False, "python": sys.version, "package": skatmind.__version__,
        "installed_module": skatmind.__file__, "wheel_sha256": digest(args.wheel.read_bytes()),
        "installed_hashes": hashes, "runs": []}
    try:
        for javascript in (True, False):
            for locale in ("de", "en"):
                key = ("js" if javascript else "native") + "-" + locale
                app = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + key)))
                server = web.start_app_web_server_v1(app, port=0, token=TOKEN)
                thread = web.serve_app_web_in_thread_v1(server)
                browser = LocalBrowser(args.browser, output / ("browser-" + key))
                item = {"key": key, "locale": locale, "javascript": javascript,
                    "browser": browser.version, "actions": [], "measurements": [], "responses": []}
                evidence["runs"].append(item)
                counts = {"import": 0, "build": 0, "activation": 0}
                def counted(name, real, counts=counts):
                    def call(*args, **kwargs):
                        counts[name] += 1
                        return real(*args, **kwargs)
                    return call
                real_headers = web.SkatMindAppWebRequestHandlerV1._headers
                def headers(handler, status, *args, item=item, real_headers=real_headers, **kwargs):
                    item["responses"].append({"method": handler.command,
                        "path": urlsplit(handler.path).path, "status": int(status)})
                    return real_headers(handler, status, *args, **kwargs)
                try:
                    cdp = browser.cdp
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                    cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
                    time.sleep(.5)
                    with (patch.object(direct, "import_workspace_bytes_into_unified_learning_v1",
                            counted("import",
                                    direct.import_workspace_bytes_into_unified_learning_v1)),
                          patch.object(web, "prepare_unified_learning_artifacts_v1",
                            counted("build", web.prepare_unified_learning_artifacts_v1)),
                          patch.object(ManagedStatefulContextV1, "activate_match",
                            counted("activation", ManagedStatefulContextV1.activate_match)),
                          patch.object(web.SkatMindAppWebRequestHandlerV1, "_headers", headers)):
                        flow(cdp, server, output, item, counts)
                    from test_session_recorded_review_web import Browser
                    client = Browser(server)
                    for route, resource in (("/assets/app.css", "assets/app.css"),
                            ("/matches/assets/capture.js", "assets/workflow.js")):
                        status, _, raw = client.request("GET", route)
                        assert status == 200 and digest(raw) == hashes[resource]
                    print(key, "completed", len(item["measurements"]), "measurements", flush=True)
                finally:
                    browser.close()
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=10)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print("Browser evidence completed:", evidence["completed"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    run(parser.parse_args())
