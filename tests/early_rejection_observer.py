"""Tests-only bounded early-response observation, independent of upload completion."""

import http.client
import select
import socket
import time
from dataclasses import dataclass, field
from io import BytesIO
from threading import Event, Thread
from types import SimpleNamespace


@dataclass
class Observation:
    supplied_bytes: int
    attempted_bytes: int = 0  # Farthest payload offset offered to socket.send.
    sent_bytes: int = 0  # Sum of actual socket.send return values, not peer receipt.
    send_calls: int = 0
    sender_outcome: str = "not_requested"
    sender_error: str | None = None
    receiver_outcome: str = "incomplete"
    receiver_error: str | None = None
    status: int | None = None
    headers: list = field(default_factory=list)
    body: bytes = b""

    def summary(self):
        return {**vars(self), "body": {"received_bytes": len(self.body)}}

    def assert_complete_html(self, status, required_headers):
        evidence = self.summary()
        assert self.receiver_outcome == "complete", evidence
        assert self.receiver_error is None, evidence
        assert self.status == status, evidence
        headers = [(name.lower(), value) for name, value in self.headers]
        assert headers.count(("content-length", str(len(self.body)))) == 1, evidence
        assert not any(name == "transfer-encoding" for name, _ in headers), evidence
        for name, value in (*required_headers, ("Connection", "close"),
                            ("Content-Type", "text/html; charset=utf-8")):
            assert headers.count((name.lower(), value)) == 1, evidence
        assert not any(name == "access-control-allow-origin" for name, _ in headers), evidence
        assert self.body.rstrip().endswith(b"</html>"), evidence
        return self.body


def _response_head(wire):
    with http.client.HTTPResponse(SimpleNamespace(makefile=lambda *args: BytesIO(wire))) as parsed:
        parsed.begin()
        headers = parsed.getheaders()
        lengths = [value for name, value in headers if name.lower() == "content-length"]
        if (len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal()
                or any(name.lower() == "transfer-encoding" for name, _ in headers)):
            raise ValueError("Missing or ambiguous response framing")
        length = int(lengths[0])
        if length > 65_536:
            raise ValueError("Response exceeds observer bound")
        return parsed.status, headers, length


def observe_early_response(port, request_headers, *, payload=None, timeout=5, connected=None):
    """Send headers, then receive while a separate worker attempts the supplied body.

    One absolute deadline and bounded response bytes apply on every path. A complete
    response can stop further sending; sender errors never create response evidence.
    Ordinary request helpers deliberately do not use this opt-in transport.
    """
    result = Observation(0 if payload is None else len(payload))
    deadline = time.monotonic() + timeout
    stop, ready, attempting = Event(), Event(), Event()
    worker = None
    client = socket.create_connection(("127.0.0.1", port), timeout=timeout)

    def remaining():
        duration = deadline - time.monotonic()
        if duration <= 0:
            raise TimeoutError("Early-response observer deadline expired")
        return duration

    def send():
        try:
            if not ready.wait(remaining()):
                raise TimeoutError("Receiver did not become ready")
            view = memoryview(payload)
            # Always attempt the supplied payload at least once. This is distinct
            # from the header-first case even if a response is already available.
            while result.sent_bytes < len(view):
                remaining()
                result.attempted_bytes = len(view)
                result.send_calls += 1
                attempting.set()
                try:
                    count = client.send(view[result.sent_bytes:])
                    if not count:
                        raise ConnectionError("Upload send returned zero")
                    result.sent_bytes += count
                except BlockingIOError:
                    if not stop.is_set():
                        select.select([], [client], [], remaining())
                if stop.is_set():
                    break
            result.sender_outcome = ("complete" if result.sent_bytes == len(view)
                                     else "stopped_by_receiver")
        except (OSError, ValueError) as error:
            result.sender_outcome = "error"
            result.sender_error = repr(error)

    try:
        if connected is not None:
            connected(client.getsockname()[1])
        client.settimeout(remaining())
        client.sendall(request_headers)
        client.setblocking(False)
        if payload is not None:
            worker = Thread(target=send, name="early-rejection-upload")
            worker.start()
        ready.set()
        if worker is not None:
            assert attempting.wait(remaining()), "Sender never attempted the supplied payload"
        wire = bytearray()
        body_start = length = None
        try:
            while True:
                readable, _, _ = select.select([client], [], [], remaining())
                if not readable:
                    raise TimeoutError("No complete response before deadline")
                chunk = client.recv(8192)
                if not chunk:
                    raise EOFError("Peer closed before a complete framed response")
                wire.extend(chunk)
                if len(wire) > 131_072:
                    raise ValueError("Response exceeds observer wire bound")
                if body_start is None and b"\r\n\r\n" in wire:
                    body_start = wire.index(b"\r\n\r\n") + 4
                    result.status, result.headers, length = _response_head(bytes(wire))
                if body_start is not None:
                    result.body = bytes(wire[body_start:])
                    if len(result.body) > length:
                        raise ValueError("Extra bytes beyond framed response")
                    if len(result.body) == length:
                        result.receiver_outcome = "complete"
                        break
        except (OSError, EOFError, ValueError, http.client.HTTPException) as error:
            result.receiver_outcome = "error"
            result.receiver_error = repr(error)
    finally:
        stop.set()
        ready.set()
        try:
            client.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # Cleanup only; never response evidence.
        client.close()
        if worker is not None:
            worker.join(timeout=timeout + 1)
            assert not worker.is_alive(), result.summary()
    return result
