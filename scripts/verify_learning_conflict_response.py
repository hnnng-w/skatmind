# ruff: noqa: E501 - Keep bounded browser probes and evidence records legible.
"""Source-tree #300 conflict delivery/recovery and valid attachment continuity probe."""

import argparse
import json
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import verify_learning_outcome_navigation as prior
from test_learning_conflict_response import competing_catalog, references
from test_learning_direct_entry_web import build, create_collection, downloads, saved_bytes
from test_learning_report_attachment_web import add_source_match, executed_source, save_other
from test_learning_report_rejection import downloaded_result

import skatmind.app_web.learning_direct_entry as direct
import skatmind.learning_corpus_import as imports
import skatmind.learning_corpus_strategy_teacher_builder as teacher
from skatmind.app_web.stateful_localization import text
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1

ADD = 'form[action="/learning/add-recorded-match"]'
UPLOAD = 'form:has(input[value="import_strategy_teacher_report"])'


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    start = time.monotonic()
    evidence = dict(completed=False, python=sys.version, cases=[],
        boundary="Disposable source-tree data; not installed UAT. Fresh profiles at default 100% zoom; no changed-layout 200% acceptance.")
    try:
        for locale, script in (("en", False), ("en", True), ("de", False), ("de", True)):
            root = args.output / f"{locale}-js{int(script)}"
            root.mkdir()
            fixture = prior.localized_server.__wrapped__(root)
            server = next(fixture)
            local = None
            counts = Counter()
            row = dict(locale=locale, javascript=script, prepared=script, phases=[], states=[], actions=[])
            evidence["cases"].append(row)
            def counted(key, real, counts=counts):
                def call(*values, **kwargs):
                    counts[key] += 1
                    return real(*values, **kwargs)
                return call
            try:
                with ExitStack() as stack:
                    for module, name, key in (
                        (direct, "import_workspace_bytes_into_unified_learning_v1", "import"),
                        (prior.learning, "prepare_learning_corpus_artifacts_web_v1", "prepare"),
                        (prior.learning, "select_current_learning_corpus_snapshot_web_v1", "select"),
                        (prior.learning, "reload_learning_corpus_web_v1", "reload"),
                        (prior.match_analysis, "execute_match_decision_analysis_v1", "analysis"),
                        (teacher, "build_match_decision_position_request_v1", "reconciliation"),
                        (imports, "save_learning_corpus_catalog_v1", "catalog_save_attempt"),
                        (imports, "publish_learning_corpus_match_snapshot_object_v1", "snapshot_publication"),
                        (prior.profiles, "save_frontend_profile_file_v1", "profile_write"),
                        (prior.match_context, "save_match_workspace_file_v1", "recording_write"),
                    ):
                        stack.enter_context(patch.object(module, name, counted(key, getattr(module, name))))
                    http = prior.Browser(server)
                    source_path, workspace, report, source = executed_source(http, server)
                    ordinary = downloaded_result(http, report)
                    source_file, ordinary_file = root / "source.json", root / "ordinary.json"
                    source_file.write_bytes(source)
                    ordinary_file.write_bytes(ordinary)
                    other_path, _ = save_other(source_path, workspace)
                    create_collection(http)
                    if script:
                        build(http, add_source_match(http, source_path))
                    prior.follow(http, http.request("GET", "/learning/recorded-matches/refresh"))
                    page = http.page("/learning/current")
                    prior.follow(http, http.submit(prior.Forms(page).find("/actions/profile/language"), language=locale))
                    active = server.app_context.managed_stateful.active_learning
                    retained = references(active)
                    home = server.app_context.managed_home.root
                    recording = source_path.read_bytes(), other_path.read_bytes()
                    files = saved_bytes(home)
                    row["phases"].append(dict(name="explicit_fixture_setup_and_locale", counts=dict(counts)))
                    local = prior.LocalBrowser(args.browser, root / "profile")
                    row["browser"] = local.version
                    cdp = local.cdp
                    name, value = http.cookie.split("=", 1)
                    cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                    cdp.call("Emulation.setDeviceMetricsOverride", width=1100, height=900, deviceScaleFactor=1, mobile=False)

                    def activate(selector, *, keyboard=False, cdp=cdp):
                        if keyboard:
                            for _ in range(200):
                                if cdp.evaluate("document.activeElement===document.querySelector(" + json.dumps(selector) + ")"):
                                    break
                                prior.keyboard(cdp, "Tab", "Tab", 9)
                            else:
                                raise AssertionError("Native Tab did not reach " + selector)
                            assert cdp.evaluate("document.activeElement.matches(':focus-visible')")
                            prior.keyboard(cdp, "Enter", "Enter", 13, "\r")
                        else:
                            from verify_recording_deletion import click
                            click(cdp, selector)
                        time.sleep(.7)
                        for _ in range(100):
                            if cdp.evaluate("document.readyState==='complete' && !!document.activeElement"):
                                break
                            time.sleep(.05)

                    def capture(label, cdp=cdp, root=root, row=row):
                        state = cdp.evaluate("""(()=>{const a=document.activeElement,e=document.querySelector('.error-summary');return {
                            path:location.pathname,status:performance.getEntriesByType('navigation')[0].responseStatus,
                            locale:document.documentElement.lang,error:e?.innerText,focus:a.id||a.className,
                            sourceControls:!!document.querySelector('#learning-sources'),richResult:!!document.querySelector('#learning-result-primary'),
                            technicalOpen:document.querySelector('#learning-result-technical')?.open,
                            fileCount:document.querySelector('input[type=file]')?.files.length,
                            receipt:document.querySelector('[data-operation-feedback]')?.innerText,
                            devicePixelRatio,scale:visualViewport.scale};})()""")
                        state["name"] = label
                        row["states"].append(state)
                        cdp.screenshot(root / (label + ".png"))
                        return state

                    def upload(path, cdp=cdp):
                        node = cdp.call("DOM.getDocument")["root"]["nodeId"]
                        field = cdp.call("DOM.querySelector", nodeId=node, selector='input[name="report_source_file"]')["nodeId"]
                        cdp.call("DOM.setFileInputFiles", nodeId=field, files=[str(path)])

                    cdp.navigate(server.origin + "/learning/current")
                    prior.choose_source(cdp, prior.source_handle(other_path if script else source_path), row)
                    original_save = imports.save_learning_corpus_catalog_v1
                    competition = []
                    def conflict(root, document, *, expected_content_fingerprint, active=active,
                                 original_save=original_save, competition=competition):
                        assert not competition
                        competition.append(competing_catalog(active))
                        return original_save(root, document, expected_content_fingerprint=expected_content_fingerprint)
                    before = counts.copy()
                    with patch.object(imports, "save_learning_corpus_catalog_v1", conflict):
                        activate(ADD + " > button", keyboard=not script)
                    rejected = capture("initial-conflict-response")
                    assert rejected["status"] == 409 and rejected["locale"] == locale
                    assert text(locale, "validation.message.language_context_conflict") in rejected["error"]
                    assert rejected["focus"] == "error-summary"
                    assert not rejected["richResult"] and not rejected["sourceControls"]
                    assert counts-before == Counter({"import": 1, "catalog_save_attempt": 1, "snapshot_publication": 1})
                    disk = load_learning_corpus_directory_v1(active.path)
                    assert disk.document == competition[0] and len(disk.orphan_match_snapshot_ids) == 1
                    assert all(a is b for a, b in zip(retained, references(active), strict=True))
                    assert recording == (source_path.read_bytes(), other_path.read_bytes())
                    row["phases"].append(dict(name="explicit_add_conflict", counts=dict(counts-before),
                        deliberate_competing_catalog_writes=1, orphan_count=1))
                    after_conflict = saved_bytes(home)
                    assert after_conflict != files
                    before = counts.copy()
                    activate('.error-summary a[href="/learning"]', keyboard=True)
                    assert capture("native-recovery-destination")["status"] == 200
                    assert counts == before and saved_bytes(home) == after_conflict
                    assert server.app_context.managed_stateful.active_learning is active
                    row["phases"].append(dict(name="passive_recovery", counts=dict(counts-before)))
                    # Reopen is explicit native recovery, never automatic response handling.
                    activate('details:has(form[action="/learning/open"]) > summary')
                    activate('form[action="/learning/open"] button', keyboard=True)
                    assert server.app_context.managed_stateful.active_learning is not active
                    assert saved_bytes(home) == after_conflict
                    row["phases"].append(dict(name="explicit_reopen", counts=dict(counts-before)))
                    if not script:
                        prior.choose_source(cdp, prior.source_handle(source_path), row)
                        before = counts.copy()
                        activate(ADD + " > button", keyboard=True)
                        row["phases"].append(dict(name="explicit_add_after_reopen", counts=dict(counts-before)))
                    before = counts.copy()
                    activate('details:has(> #learning-sources) > summary')
                    upload(ordinary_file)
                    activate(UPLOAD + " button", keyboard=not script)
                    invalid = capture("ordinary-report-rejection")
                    assert invalid["status"] == 400 and invalid["fileCount"] == 0
                    assert text(locale, "validation.report_file.format") in invalid["error"]
                    assert counts == before
                    upload(source_file)
                    activate(UPLOAD + " button", keyboard=not script)
                    accepted = capture("valid-report-retry")
                    assert text(locale, "feedback.report_attached") in accepted["receipt"]
                    assert counts-before == Counter(reconciliation=1)
                    row["phases"].append(dict(name="explicit_attachment_retry", counts=dict(counts-before)))
                    activate('details:has(> #learning-build) > summary')
                    before = counts.copy()
                    activate(prior.BUILD, keyboard=not script)
                    prepared = capture("compact-result-after-recovery")
                    assert prepared["status"] == 200 and prepared["focus"] == "learning-results"
                    assert prepared["richResult"] and not prepared["technicalOpen"]
                    assert counts-before == Counter(prepare=1, reconciliation=1)
                    row["phases"].append(dict(name="explicit_preparation", counts=dict(counts-before)))
                    artifacts = downloads(http)
                    row["download_hashes"] = {k: prior.digest(v[1]) for k, v in artifacts.items()}
                    assert len(artifacts) == 10
                    row["completed"] = True
            finally:
                if local:
                    local.close()
                fixture.close()
        evidence["completed"] = True
    finally:
        evidence["seconds"] = round(time.monotonic()-start, 3)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(dict(completed=evidence["completed"], seconds=evidence["seconds"], output=str(args.output))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
