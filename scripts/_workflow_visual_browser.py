"""Optional local Chromium DevTools transport, reused from #222/#223 evidence.

This is verification tooling, never imported by the application or full check.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen


class DevTools:
    def __init__(self, url):
        parsed = urlsplit(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=90)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall((
            f"GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        header = b""
        while not header.endswith(b"\r\n\r\n"):
            header += self.read(1)
        if b" 101 " not in header:
            raise RuntimeError("Local DevTools handshake failed.")
        self.sequence = 0
        self.events = []
        self.script_disabled = False

    def read(self, count):
        data = b""
        while len(data) < count:
            chunk = self.socket.recv(count - len(data))
            if not chunk:
                raise RuntimeError("Local DevTools connection closed.")
            data += chunk
        return data

    def call(self, method, **params):
        if method == "Emulation.setScriptExecutionDisabled":
            self.script_disabled = params["value"]
        self.sequence += 1
        data = json.dumps({"id": self.sequence, "method": method, "params": params}).encode()
        size = len(data)
        if size < 126:
            prefix = bytes([0x81, 0x80 | size])
        elif size < 65536:
            prefix = bytes([0x81, 0xfe]) + struct.pack("!H", size)
        else:
            prefix = bytes([0x81, 0xff]) + struct.pack("!Q", size)
        mask = os.urandom(4)
        self.socket.sendall(prefix + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(data)))
        while True:
            head = self.read(2)
            size = head[1] & 127
            if size == 126:
                size = struct.unpack("!H", self.read(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self.read(8))[0]
            value = json.loads(self.read(size))
            if value.get("method") == "Network.requestWillBeSent":
                self.events.append(value)
            if value.get("id") == self.sequence:
                if "error" in value:
                    raise RuntimeError(value["error"])
                return value.get("result", {})

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result["result"].get("value")

    def navigate(self, url):
        self.call("Page.navigate", url=url)
        time.sleep(.5)
        for _ in range(100):
            if self.evaluate("document.readyState==='complete' && location.href==="
                             + json.dumps(url)):
                return
            time.sleep(.1)
        raise RuntimeError("Page did not finish loading.")

    def activate(self, selector):
        """Use real keyboard Enter; evaluation only locates/focuses the control."""
        self.evaluate(f"document.querySelector({json.dumps(selector)}).scrollIntoView("
                      "{block:'center'});")
        self.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
        self.call("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter",
                  windowsVirtualKeyCode=13, text="\r")
        self.call("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter",
                  windowsVirtualKeyCode=13)
        time.sleep(.6)

    def screenshot(self, path, *, whole=False):
        self.evaluate("window.scrollTo(0,0)" if whole else "void 0")
        params = {}
        if whole:
            size = self.call("Page.getLayoutMetrics")["cssContentSize"]
            params["clip"] = {"x": 0, "y": 0, "width": size["width"],
                              "height": size["height"], "scale": 1}
        shot = self.call("Page.captureScreenshot", format="png",
                         captureBeyondViewport=whole, **params)
        path.write_bytes(base64.b64decode(shot["data"]))


class LocalBrowser:
    def __init__(self, executable: Path, profile: Path):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        self.process = subprocess.Popen([
            str(executable), "--headless=new", "--disable-gpu",
            f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
            "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
            "--disable-sync", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                    tabs = json.load(response)
                break
            except OSError:
                time.sleep(.1)
        else:
            self.close()
            raise RuntimeError("Local browser DevTools did not start.")
        self.cdp = DevTools(tabs[0]["webSocketDebuggerUrl"])
        self.version = self.cdp.call("Browser.getVersion")
        target = self.cdp.call("Target.createTarget", url="about:blank")["targetId"]
        with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
            tabs = json.load(response)
        self.cdp.socket.close()
        self.cdp = DevTools(next(t for t in tabs if t["id"] == target)["webSocketDebuggerUrl"])
        self.cdp.call("Page.enable")
        self.cdp.call("Network.enable")
        self.cdp.call("Page.bringToFront")

    def close(self):
        if self.process.poll() is None:
            if hasattr(self, "cdp"):
                try:
                    self.cdp.call("Browser.close")
                    self.process.wait(timeout=15)
                    return
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    pass
            self.process.terminate()
            self.process.wait(timeout=20)
