"""Optional dependency-free installed-Wheel browser evidence in fresh synthetic homes."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import time
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode, urlsplit

from _workflow_visual_browser import LocalBrowser

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import (
    SkatMindAppWebRequestHandlerV1,
    serve_app_web_in_thread_v1,
    start_app_web_server_v1,
)

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("recording_deletion.py", "recording_deletion_http.py", "context.py",
    "form_registry.py", "server.py", "language_context.py", "language_form_preservation.py",
    "session_frontend.py", "match_frontend.py", "recorded_review_opening.py",
    "friendly_creation_rendering.py", "recorded_review_rendering.py", "assets/app.css",
    "assets/workflow.js", "locales/de.json", "locales/en.json", "templates/app.html")
TOKEN = "synthetic-deletion-browser-evidence"
PREVIEW = 'form[action="/recordings/delete/preview"]'
APPLY = 'form[action="/recordings/delete/apply"]'
CANCEL = 'form[action="/recordings/delete/cancel"]'
CHECKBOX = APPLY + ' input[name="confirm_delete"]'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def request(server, method, route, values=None):
    client = http.client.HTTPConnection("127.0.0.1", server.port, timeout=30)
    client.request(method, route, body=None if values is None else urlencode(values).encode(),
        headers={"Cookie": "skatmind_app_token=" + TOKEN, "Origin": server.origin,
                 "Content-Type": "application/x-www-form-urlencoded"})
    response = client.getresponse()
    result = response.status, response.read()
    client.close()
    return result


class OpenForms(HTMLParser):
    def __init__(self, html, route):
        super().__init__()
        self.route, self.current, self.forms = route, None, []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = {} if attrs.get("action") == self.route else None
            if self.current is not None:
                self.forms.append(self.current)
        if tag == "input" and self.current is not None and "name" in attrs:
            self.current[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


def competing_open(server, family, target, evidence):
    status, raw = request(server, "GET", f"/{family}")
    assert status == 200
    values = next(form for form in OpenForms(raw.decode(), f"/{family}/open").forms
                  if form["handle"] == target.handle)
    assert request(server, "POST", f"/{family}/open", values)[0] == 303
    evidence["competing_http"].append(f"/{family}/open")


def keyboard(cdp, key, code, number, text=None):
    arguments = dict(type="keyDown", key=key, code=code, windowsVirtualKeyCode=number)
    if text is not None:
        arguments["text"] = text
    cdp.call("Input.dispatchKeyEvent", **arguments)
    cdp.call("Input.dispatchKeyEvent", type="keyUp", key=key, code=code,
             windowsVirtualKeyCode=number)


def choose(cdp):
    cdp.evaluate(f"document.querySelector({json.dumps(CHECKBOX)}).scrollIntoView();"
                 f"document.querySelector({json.dumps(CHECKBOX)}).focus()")
    keyboard(cdp, " ", "Space", 32, " ")


def focus(cdp):
    return cdp.evaluate("""(() => {const e=document.activeElement,s=getComputedStyle(e);
        return {tag:e.tagName,name:e.name||null,outline:s.outlineColor,width:s.outlineWidth,
                visible:e.matches(':focus-visible')};})()""")


def submit(cdp, selector, evidence, name, *, expected_posts=1):
    cdp.events.clear()
    cdp.activate(selector)
    cdp.evaluate("void 0")
    paths = [urlsplit(event["params"]["request"]["url"]).path for event in cdp.events
             if event["params"]["request"]["method"] == "POST"]
    assert len(paths) == expected_posts, (name, paths)
    evidence["actions"].append({"name": name, "posts": paths,
        "path": cdp.evaluate("location.pathname"), "focus": focus(cdp)})


def measure(cdp, output, evidence, name, selector, *, all_sizes=True):
    sizes = ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2))
    for width, height, scale in sizes if all_sizes else ((320, 800, 1),):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                 deviceScaleFactor=1, mobile=False)
        if scale == 2:
            cdp.evaluate("""(() => {const a=[...document.querySelectorAll('body,body *')];
                const s=a.map(e=>parseFloat(getComputedStyle(e).fontSize));
                a.forEach((e,i)=>e.style.fontSize=s[i]*2+'px');})()""")
        result = cdp.evaluate("""(selector => {const e=document.querySelector(selector);
            if(!e)throw Error('Required measured element is absent');
            const r=e.getBoundingClientRect();return {client:document.documentElement.clientWidth,
            scroll:document.documentElement.scrollWidth,width:r.width,height:r.height,
            text:e.innerText,checked:!!document.querySelector('[name=confirm_delete]:checked'),
            overflow:[...document.querySelectorAll('main *')].filter(e=>e.checkVisibility() &&
                e.getBoundingClientRect().right>document.documentElement.clientWidth+1).map(e=>({
                    tag:e.tagName,classes:e.className,text:e.innerText,
                    width:e.getBoundingClientRect().width,
                    columns:getComputedStyle(e).gridTemplateColumns})),
            path:location.pathname};})(""" + json.dumps(selector) + ")")
        evidence["measurements"].append({"name": name, "viewport": [width, height],
            "text_scale": scale, "focus": focus(cdp), **result})
        cdp.evaluate(f"document.querySelector({json.dumps(selector)}).scrollIntoView()")
        cdp.screenshot(output / f"{evidence['key']}-{name}-{width}-{scale}.png")
        if selector == "#recording-deletion":
            cdp.evaluate(f"document.querySelector({json.dumps(APPLY)}).scrollIntoView()")
            cdp.screenshot(output / f"{evidence['key']}-{name}-{width}-{scale}-controls.png")
        assert result["client"] == result["scroll"], (name, result)
        assert result["height"] > 0 and result["width"] > 0
        if scale == 2:
            cdp.evaluate("document.querySelectorAll('body,body *').forEach(e=>"
                         "e.style.removeProperty('font-size'))")


def create(cdp, server, family, evidence):
    cdp.navigate(server.origin + ("/sessions" if family == "sessions" else "/matches/new"))
    route = "/sessions/create" if family == "sessions" else "/matches/api/v1/create"
    selector = f'form[action="{route}"]'
    title_field = "game_name" if family == "sessions" else "match_title"
    values = {title_field: ("Repeated synthetic recording " + "LongTitle" * 14)[:160],
        "forehand_name": "Alexandra Long-Synthetic-Name", "middlehand_name": "Boris",
        "rearhand_name": "Clara"}
    for name, value in values.items():
        control = selector + f' [name="{name}"]'
        cdp.evaluate(f"document.querySelector({json.dumps(control)}).focus()")
        cdp.call("Input.insertText", text=value)
    # Native select defaults are retained except the deliberately chosen perspective.
    cdp.evaluate(f"document.querySelector('{selector} [name=perspective_seat]').focus()")
    keyboard(cdp, "ArrowDown", "ArrowDown", 40)
    submit(cdp, selector + ' button[value="update"]', evidence, family + "-setup")
    submit(cdp, selector + ' button[value="create"]', evidence, family + "-create")
    active = getattr(server.app_context.managed_stateful,
                     "active_session" if family == "sessions" else "active_match")
    assert active is not None and active.path.is_file()
    return active


def flow(cdp, server, output, evidence, removals):
    app, locale = server.app_context, evidence["locale"]
    cdp.navigate(server.origin + "/sessions")
    submit(cdp, f'.language-selector button[value="{locale}"]', evidence, "initial-language")
    for family in ("sessions", "matches"):
        first, second = create(cdp, server, family, evidence), create(cdp, server, family, evidence)
        assert first.path != second.path
        for index, target in enumerate((first, second)):
            prefix = family + ("-inactive" if index == 0 else "-active")
            route = f"/{family}" if index == 0 else "/review/recorded"
            other = second if index == 0 else None
            other_bytes = None if other is None else other.path.read_bytes()
            original = target.path.read_bytes()
            cdp.navigate(server.origin + route)
            measure(cdp, output, evidence, prefix + "-list", "main")
            selection = PREVIEW + f':has(input[value="{target.handle}"]) button'
            before = len(removals)
            profile = app.frontend_profile.profile_path.read_bytes()
            submit(cdp, selection, evidence, prefix + "-preview")
            assert len(removals) == before and target.path.read_bytes() == original
            assert cdp.evaluate("document.activeElement.name") != "confirm_delete"
            assert not cdp.evaluate("!!document.querySelector('[name=confirm_delete]:checked')")
            measure(cdp, output, evidence, prefix + "-preview", "#recording-deletion")
            submit(cdp, CANCEL + " button", evidence, prefix + "-cancel")
            assert target.path.read_bytes() == original and len(removals) == before
            assert app.frontend_profile.profile_path.read_bytes() == profile
            cdp.navigate(server.origin + route)
            submit(cdp, selection, evidence, prefix + "-fresh-preview")
            pending = app.recording_deletion.pending
            choose(cdp)
            assert cdp.evaluate("!!document.querySelector('[name=confirm_delete]:checked')")
            assert focus(cdp)["visible"] and focus(cdp)["width"] != "0px"
            cdp.screenshot(output / f"{evidence['key']}-{prefix}-checked-focus.png")
            evidence["actions"].append({"name": prefix + "-checked", "posts": [],
                                        "focus": focus(cdp)})
            for language in ("en" if locale == "de" else "de", locale):
                submit(cdp, f'.language-selector button[value="{language}"]', evidence,
                       prefix + "-language-" + language)
                assert app.recording_deletion.pending is pending
                assert not cdp.evaluate("!!document.querySelector('[name=confirm_delete]:checked')")
            measure(cdp, output, evidence, prefix + "-language-cleared", "#recording-deletion")
            submit(cdp, APPLY + " button", evidence, prefix + "-unchecked", expected_posts=0)
            assert cdp.evaluate("document.activeElement.name") == "confirm_delete"
            assert len(removals) == before and target.path.read_bytes() == original
            competing_open(server, family, target, evidence)
            choose(cdp)
            submit(cdp, APPLY + " button", evidence, prefix + "-stale")
            assert cdp.evaluate("!!document.querySelector('.error-summary')")
            assert len(removals) == before and target.path.read_bytes() == original
            measure(cdp, output, evidence, prefix + "-stale", "main", all_sizes=False)
            if other is not None:
                competing_open(server, family, other, evidence)
            cdp.navigate(server.origin + route)
            submit(cdp, selection, evidence, prefix + "-final-preview")
            profile = app.frontend_profile.profile_path.read_bytes()
            choose(cdp)
            submit(cdp, APPLY + " button", evidence, prefix + "-delete")
            assert len(removals) == before + 1 and not target.path.exists()
            assert app.frontend_profile.profile_path.read_bytes() == profile
            if other is not None:
                assert other.path.read_bytes() == other_bytes
            evidence["files"].append({"name": prefix, "removed_count": 1,
                "source_sha256": digest(original), "profile_sha256": digest(profile),
                "remaining_sha256": None if other_bytes is None else digest(other_bytes),
                "target_absent": True, "profile_unchanged": True})
            measure(cdp, output, evidence, prefix + "-deleted", "main", all_sizes=False)


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh scratch directory under an existing parent.")
    installed = not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    assert installed, "Install the Wheel independently"
    hashes = {}
    for name in MODULES:
        raw = files("skatmind.app_web").joinpath(name).read_bytes()
        assert raw == (ROOT / "src/skatmind/app_web" / name).read_bytes(), name
        hashes[name] = digest(raw)
    output.mkdir()
    evidence = {"completed": False, "python": sys.version, "package": skatmind.__version__,
        "module": skatmind.__file__, "wheel_sha256": digest(args.wheel.read_bytes()),
        "installed_hashes": hashes, "runs": []}
    try:
        for javascript in (True, False):
            for locale in ("de", "en"):
                key = ("js" if javascript else "native") + "-" + locale
                app = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + key)))
                server = start_app_web_server_v1(app, port=0, token=TOKEN)
                thread = serve_app_web_in_thread_v1(server)
                browser = LocalBrowser(args.browser, output / ("browser-" + key))
                item = {"key": key, "locale": locale, "javascript": javascript,
                    "browser": browser.version, "actions": [], "measurements": [],
                    "files": [], "competing_http": [], "responses": []}
                evidence["runs"].append(item)
                removals = []
                real = Path.unlink
                def counted(path, *args, real=real, app=app, removals=removals, **kwargs):
                    result = real(path, *args, **kwargs)
                    if path.parent in (app.managed_stateful.root("sessions"),
                                       app.managed_stateful.root("matches")):
                        removals.append(path)
                    return result
                real_headers = SkatMindAppWebRequestHandlerV1._headers
                def headers(handler, status, *args, real_headers=real_headers, item=item, **kwargs):
                    item["responses"].append({"method": handler.command,
                        "path": urlsplit(handler.path).path, "status": int(status)})
                    return real_headers(handler, status, *args, **kwargs)
                try:
                    cdp = browser.cdp
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                    cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
                    time.sleep(.5)
                    with (patch.object(Path, "unlink", counted),
                          patch.object(SkatMindAppWebRequestHandlerV1, "_headers", headers)):
                        flow(cdp, server, output, item, removals)
                    for route, name in (("/assets/app.css", "assets/app.css"),
                                        ("/matches/assets/capture.js", "assets/workflow.js")):
                        status, raw = request(server, "GET", route)
                        assert status == 200 and digest(raw) == hashes[name]
                    item["actual_removals"] = len(removals)
                    assert len(removals) == 4
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
