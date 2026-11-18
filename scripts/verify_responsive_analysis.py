"""Compact #326 source-browser check with synthetic data and page JavaScript disabled."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from _workflow_visual_browser import LocalBrowser
from verify_analysis_controls import choose, click, wait

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import pytest  # noqa: E402
from test_analysis_controls_web import last_match  # noqa: E402
from test_automatic_historical_evidence import genuine_historical  # noqa: E402
from test_automatic_historical_learning import retain_fixture  # noqa: E402
from test_automatic_match_learning_evidence import forbid_execution  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402

from skatmind.app_web.stateful_localization import text  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    browser = None
    report = {"completed": False, "python": sys.version, "page_javascript": False,
              "observations": []}
    try:
        http, source, _page = last_match(server)
        retain_fixture(server.app_context, genuine_historical.__wrapped__())
        original = source.read_bytes()
        store = server.app_context.saved_match_analyses.store
        manifest = store.snapshot().manifest
        browser = LocalBrowser(args.browser, args.output / "browser-profile")
        cdp = browser.cdp
        report["browser"] = browser.version
        name, value = http.cookie.split("=", 1)
        cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        form = 'form[action="/matches/review-whole-game"]'
        with pytest.MonkeyPatch.context() as patch:
            calls = forbid_execution(patch)
            for locale in ("de", "en"):
                cdp.navigate(server.origin + "/matches/review/2")
                click(cdp, f'form[action="/actions/profile/language"] button[value="{locale}"]')
                wait(cdp, f'document.documentElement.lang === "{locale}"')
                click(cdp, form + " button.primary")
                wait(cdp, '!!document.querySelector("#forced-card-guidance")')
                body = cdp.evaluate("document.body.innerText")
                assert text(locale, "analysis.forced_card_help") in body
                assert "100%" not in body and "100 %" not in body
                click(cdp, 'main a[href="/matches/review/2"]')
                # Native links use Enter as well; the shared click helper focuses links.
                from verify_recording_deletion import keyboard
                keyboard(cdp, "Enter", "Enter", 13, "\r")
                wait(cdp, "!!document.querySelector(" + json.dumps(form) + ")")
                click(cdp, form + " details > summary")
                choose(cdp, form + ' [name="settings_mode"]', 1)
                assert cdp.evaluate("document.querySelector(" + json.dumps(
                    form + ' [name="settings_mode"]') + ").value") == "custom"
                cdp.navigate(server.origin + "/review/saved")
                body = cdp.evaluate("document.body.innerText")
                for key in ("inputs", "evidence", "open_input", "view_analysis",
                            "saved_relationship"):
                    assert text(locale, "historical_learning." + key) in body
                report["observations"].append({"locale": locale, "forced_hint": True,
                    "custom_control": True, "saved_input_and_analysis_labels": True})
            assert calls == []
        assert source.read_bytes() == original and store.snapshot().manifest == manifest
        report.update(completed=True, new_analysis_executions=0,
                      source_sha256=hashlib.sha256(original).hexdigest())
    finally:
        if browser is not None:
            browser.close()
        fixture.close()
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
