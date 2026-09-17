"""Bounded rejection lifecycle evidence, independently of OS-specific TCP resets."""

import http.client
import socket
from io import BufferedReader, BytesIO
from threading import Event, current_thread
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest
from test_compact_card_entry_web import choice_codes, create_live
from test_frontend_language_switching import localized_server as _localized_server
from test_local_learning_corpus_web import _ShutdownObserver
from test_session_card_feedback_web import snapshot, start_play
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.server as server_module
from skatmind.app_web.security import app_web_security_headers_v1

Handler = server_module.SkatMindAppWebRequestHandlerV1


@pytest.fixture
def localized_server(tmp_path):
    # Join daemon request workers too: server_close alone only joins non-daemon workers.
    fixture = _localized_server.__wrapped__(tmp_path)
    server = next(fixture)
    workers = []
    original = server.finish_request

    def finish_request(request, address):
        workers.append(current_thread())
        original(request, address)

    server.finish_request = finish_request
    try:
        yield server
    finally:
        fixture.close()
        for worker in workers:
            worker.join(timeout=5)
        assert not any(worker.is_alive() for worker in workers)


def assert_response(response, expected):
    assert response.status == expected
    content = response.read()
    assert response.getheaders().count(("Content-Length", str(len(content)))) == 1
    assert response.getheader("Transfer-Encoding") is None
    assert response.getheader("Content-Type") == "text/html; charset=utf-8"
    assert content.endswith(b"</html>") or content.endswith(b"</html>\n")
    assert b"session-card-evidence" not in content
    for name, value in app_web_security_headers_v1():
        assert response.getheader(name) == value
    assert response.getheader("Access-Control-Allow-Origin") is None
    return content


def wire_request(browser, route, body, *, framing=None, origin=None):
    server = browser.server
    return (
        f"POST {route} HTTP/1.1\r\nHost: 127.0.0.1:{server.port}\r\n"
        f"Cookie: {browser.cookie}\r\nOrigin: {origin or server.origin}\r\n"
        "Content-Type: application/x-www-form-urlencoded\r\n"
        + (f"Content-Length: {len(body)}\r\n" if framing is None else framing)
        + "\r\n"
    ).encode()


class Lifecycle:
    def __init__(self, server, monkeypatch):
        self.client_port = None
        self.closed, self.discarding, self.first_chunk = Event(), Event(), Event()
        self.discarded = bytearray()
        self.statuses, self.events, self.body_reads = [], [], []
        self.shutdown = _ShutdownObserver(server.shutdown_request, self.closed)
        original_setup, original_headers = Handler.setup, Handler._headers

        def setup(handler):
            original_setup(handler)
            read, read1, write = handler.rfile.read, handler.rfile.read1, handler.wfile.write

            def observed_read(size):
                data = read(size)
                self.body_reads.append(len(data))
                self.events.append("body")
                return data

            def observed_read1(size):
                self.discarding.set()
                data = read1(size)
                self.discarded.extend(data)
                self.events.append("discard")
                if data:
                    self.first_chunk.set()
                return data

            def observed_write(content):
                result = write(content)
                self.events.append("write")
                return result

            handler.rfile.read = observed_read
            handler.rfile.read1 = observed_read1
            handler.wfile.write = observed_write

        def headers(handler, status, *args, **kwargs):
            self.shutdown.observe_headers(handler, self.client_port)
            self.statuses.append(status)
            original_headers(handler, status, *args, **kwargs)

        monkeypatch.setattr(Handler, "setup", setup)
        monkeypatch.setattr(Handler, "_headers", headers)
        monkeypatch.setattr(server, "shutdown_request", self.shutdown)


@pytest.mark.parametrize("route", ("/sessions/cards", "/sessions/play"))
@pytest.mark.parametrize("delivery", ("late", "prefetched"))
def test_staged_oversize_response_precedes_split_discard_and_shutdown(
    localized_server, monkeypatch, route, delivery,
):
    browser = Browser(localized_server)
    if route.endswith("play"):
        active = start_play(browser)
    else:
        create_live(browser)
        active = localized_server.app_context.managed_stateful.active_session
    form = Forms(browser.page()).find(route)
    before = snapshot(active)
    body = b"X" * 8193
    valid_body = urlencode({**form["values"], "cards": "C7"}).encode()
    pipeline = wire_request(browser, route, valid_body) + valid_body
    product_calls = []

    def forbidden(*args, **kwargs):
        product_calls.append(args)
        raise AssertionError("Rejected transport reached semantic preparation")

    with monkeypatch.context() as patch:
        observation = Lifecycle(localized_server, patch)
        patch.setattr(Handler, "_prepare_form_submission", forbidden)
        patch.setattr(Handler, "_stateful_post", forbidden)
        prefetched = []
        if delivery == "prefetched":
            original_read_body = Handler._read_body

            def read_body(handler, **kwargs):
                # Test-only forced prefetch models BufferedReader header read-ahead.
                prefetched.append(handler.rfile.peek(1))
                return original_read_body(handler, **kwargs)

            patch.setattr(Handler, "_read_body", read_body)
        with socket.create_connection(("127.0.0.1", localized_server.port), timeout=3) as client:
            observation.client_port = client.getsockname()[1]
            initial = body[:17] if delivery == "prefetched" else b""
            client.sendall(wire_request(browser, route, body) + initial)
            with http.client.HTTPResponse(client) as response:
                response.begin()
                assert_response(response, 413)
                assert response.getheader("Connection") == "close"
                # The full response is readable before the promised body is complete.
            assert observation.discarding.wait(2), (
                f"No staged cleanup; closed={observation.closed.is_set()}, "
                f"body_reads={observation.body_reads}, events={observation.events}"
            )
            assert not observation.closed.is_set()
            assert client.recv(1) == b""  # Server has half-closed its sending direction.
            if delivery == "late":
                client.sendall(body[:17])
            assert observation.first_chunk.wait(2)
            client.sendall(body[17:] + pipeline)
            client.shutdown(socket.SHUT_WR)
            assert observation.closed.wait(2)
        assert observation.discarded == body + pipeline
        assert observation.body_reads == []
        assert observation.statuses == [413]
        assert observation.events[:2] == ["write", "write"]
        assert prefetched == ([body[:17]] if delivery == "prefetched" else [])
        assert product_calls == [] and snapshot(active) == before
    # Use an actual returned selection and the real operation on a fresh connection.
    page = browser.page()
    card = choice_codes(page, mode="play" if route.endswith("play") else "set")[0]
    result = browser.submit(Forms(page).find(route), cards=card)
    assert result[0] == 303 and result[2] == b""
    # Initial Card entry also supplies the existing missing game metadata Command.
    assert active.state.revision == before[1].state.revision + (1 if route.endswith("play") else 2)
    assert active.state.command_log[-1].command.card == card


@pytest.mark.parametrize("route", ("/sessions/cards", "/sessions/play"))
@pytest.mark.parametrize("framing,origin,expected", (
    ("Content-Length: 8193\r\n", None, 413),
    ("Content-Length: 999999999999\r\n", "null", 403),
    ("Content-Length: 8193\r\n", "http://foreign.invalid", 403),
    ("Content-Length: 5\r\n", "null", 403),
    ("Content-Length: 5\r\nContent-Length: 5\r\n", None, 400),
    ("Transfer-Encoding: chunked\r\nContent-Length: 5\r\n", None, 400),
    ("", None, 400),
))
def test_absent_body_is_rejected_before_preparation_with_bounded_cleanup(
    localized_server, monkeypatch, route, framing, origin, expected,
):
    browser = Browser(localized_server)
    create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = snapshot(active)
    observation = Lifecycle(localized_server, monkeypatch)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError("Invalid framing or authorization reached preparation")

    monkeypatch.setattr(Handler, "_prepare_form_submission", forbidden)
    monkeypatch.setattr(Handler, "_stateful_post", forbidden)
    with socket.create_connection(("127.0.0.1", localized_server.port), timeout=3) as client:
        observation.client_port = client.getsockname()[1]
        client.sendall(wire_request(browser, route, b"", framing=framing, origin=origin))
        with http.client.HTTPResponse(client) as response:
            response.begin()
            content = assert_response(response, expected)
            assert response.getheader("Connection") == "close"
            if expected == 403:
                assert b"This request could not be authorized." in content
        # Keep the peer open: completion must come from the server's deadline.
        assert observation.closed.wait(2), "Cleanup waited for the declared body or EOF"
        assert client.recv(1) == b""
    assert observation.body_reads == [] and observation.discarded == b""
    assert observation.statuses == [expected] and calls == []
    assert snapshot(active) == before


@pytest.mark.parametrize("ending", ("excess", "departed"))
def test_cleanup_caps_excess_input_and_accepts_early_peer_departure(
    localized_server, monkeypatch, ending,
):
    browser = Browser(localized_server)
    create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = snapshot(active)
    observation = Lifecycle(localized_server, monkeypatch)
    client = socket.create_connection(("127.0.0.1", localized_server.port), timeout=3)
    try:
        observation.client_port = client.getsockname()[1]
        client.sendall(wire_request(browser, "/sessions/cards", b"",
                                    framing="Content-Length: 1000000\r\n"))
        with http.client.HTTPResponse(client) as response:
            response.begin()
            assert_response(response, 413)
        assert observation.discarding.wait(2)
        if ending == "excess":
            client.sendall(b"X" * (65_536 + 1024))
        else:
            # Leave without supplying the advertised body after reading the response.
            client.close()
        assert observation.closed.wait(2)
    finally:
        client.close()
    assert len(observation.discarded) == (65_536 if ending == "excess" else 0)
    assert observation.statuses == [413] and observation.body_reads == []
    assert snapshot(active) == before


def test_peer_departure_before_response_write_never_triggers_another_response(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = snapshot(active)
    observation = Lifecycle(localized_server, monkeypatch)
    entered, release = Event(), Event()
    headers = Handler._headers
    errors = []

    def paused(handler, status, *args, **kwargs):
        observation.shutdown.observe_headers(handler, observation.client_port)
        entered.set()
        assert release.wait(2)
        headers(handler, status, *args, **kwargs)

    monkeypatch.setattr(Handler, "_headers", paused)
    monkeypatch.setattr(localized_server, "handle_error", lambda *args: errors.append(args))
    try:
        with socket.create_connection(("127.0.0.1", localized_server.port), timeout=3) as client:
            observation.client_port = client.getsockname()[1]
            client.sendall(wire_request(browser, "/sessions/cards", b"",
                                        framing="Content-Length: 8193\r\n"))
            assert entered.wait(2)
            client.shutdown(socket.SHUT_RDWR)
    finally:
        release.set()
    assert observation.closed.wait(2)
    assert observation.statuses == [413] and errors == []
    assert snapshot(active) == before


def transport_handler():
    handler = object.__new__(Handler)
    handler.request_version = "HTTP/1.1"
    handler.requestline = "POST /sessions/play HTTP/1.1"
    handler.command = "POST"
    handler.wfile = BytesIO()
    handler.rfile = BytesIO()
    handler.close_connection = False
    timeouts, shutdowns = [], []
    handler.connection = SimpleNamespace(settimeout=timeouts.append, shutdown=shutdowns.append)
    return handler, timeouts, shutdowns


@pytest.mark.parametrize("bound", ("bytes", "deadline"))
def test_cleanup_has_small_reads_byte_cap_and_absolute_deadline(monkeypatch, bound):
    handler, timeouts, shutdowns = transport_handler()
    elapsed = 0.0
    reads, sizes = [], []

    def read1(size):
        nonlocal elapsed
        assert shutdowns == [socket.SHUT_WR]
        assert handler.wfile.getvalue().endswith(b"\r\n\r\nRejected")
        reads.append(size)
        if bound == "deadline":
            elapsed += 0.125
            data = b"X"
        else:
            data = b"X" * min(size, 3073)
        sizes.append(len(data))
        return data

    handler.rfile = SimpleNamespace(read1=read1)
    monkeypatch.setattr(server_module, "monotonic", lambda: elapsed)
    handler._send_bytes(413, b"Rejected", content_type="text/plain")
    assert handler.close_connection is True
    assert max(reads) <= 8192
    if bound == "bytes":
        assert sum(sizes) == 65_536 and reads[-1] < 8192
    else:
        assert sizes == [1, 1]
        assert timeouts == [0.25, 0.25, 0.125]


def test_cleanup_consumes_buffered_input_before_raw_input():
    handler, _, shutdowns = transport_handler()
    raw = BytesIO(b"header\n" + b"X" * 8193)
    handler.rfile = BufferedReader(raw)
    assert handler.rfile.readline() == b"header\n"
    assert raw.tell() > 7  # Confirm read-ahead, rather than merely supplying raw bytes.
    reads = []
    read1 = handler.rfile.read1

    def observed(size):
        data = read1(size)
        reads.append(data)
        return data

    handler.rfile.read1 = observed
    handler._send_bytes(400, b"Rejected", content_type="text/plain")
    assert b"".join(reads) == b"X" * 8193
    assert shutdowns == [socket.SHUT_WR] and handler.close_connection is True


@pytest.mark.parametrize("status", (200, 303, 400, 403, 413))
@pytest.mark.parametrize("failed_write", (1, 2))
def test_partial_transport_write_never_sends_second_filesystem_response(status, failed_write):
    handler, timeouts, shutdowns = transport_handler()
    writes, reads = [], []

    class BrokenWriter(BytesIO):
        def write(self, content):
            writes.append(content)
            if len(writes) == failed_write:
                super().write(content[:2])
                raise BrokenPipeError("Injected partial transport write")
            return super().write(content)

    handler.wfile = BrokenWriter()
    handler.rfile = SimpleNamespace(read1=reads.append)
    # Exercise do_POST's OSError handling too, not only the byte-writing helper.
    handler.path = "/sessions/play"

    def authorization_response():
        handler._send_bytes(status, b"Synthetic response", content_type="text/plain")
        return False

    handler._authorize_mutation = authorization_response
    handler._error_page = lambda *args, **kwargs: pytest.fail("Second filesystem response")
    handler.do_POST()
    assert len(writes) == failed_write and reads == shutdowns == []
    assert handler.close_connection is True
    assert timeouts == ([0.25] if status >= 400 else [])


@pytest.mark.parametrize("status", (200, 303))
def test_successful_responses_do_not_drain_or_change_socket_timeout(status):
    handler, timeouts, shutdowns = transport_handler()
    handler.rfile = SimpleNamespace(read1=lambda size: pytest.fail("Successful response drained"))
    handler._send_bytes(status, b"Accepted", content_type="text/plain")
    assert timeouts == shutdowns == []
    assert handler.wfile.getvalue().endswith(b"\r\n\r\nAccepted")


def test_non_transport_error_is_not_swallowed():
    handler, _, _ = transport_handler()

    def fail(*args, **kwargs):
        raise ValueError("Injected programming error")

    handler._headers = fail
    with pytest.raises(ValueError, match="Injected programming error"):
        handler._send_bytes(413, b"Rejected", content_type="text/plain")
