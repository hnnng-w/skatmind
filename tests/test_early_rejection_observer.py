"""Negative observer self-checks; these synthetic peers are not Product evidence."""

import socket
from threading import Event, Thread

import pytest
from early_rejection_observer import observe_early_response

HTML = b"<html>Failure</html>\n"
LENGTH = f"Content-Length: {len(HTML)}\r\n".encode()
HEAD = b"HTTP/1.0 413 Too Large\r\n" + LENGTH + b"Connection: close\r\n"
TYPE = b"Content-Type: text/html; charset=utf-8\r\n\r\n"


@pytest.mark.parametrize("fault", (
    "wrong_status", "missing", "truncated", "missing_length", "duplicate_length", "timeout",
))
def test_observer_cannot_manufacture_complete_rejection(fault):
    release = Event()
    errors = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(5)

        def peer():
            try:
                with listener.accept()[0] as connection:
                    connection.settimeout(5)
                    request = bytearray()
                    while not request.endswith(b"\r\n\r\n"):
                        chunk = connection.recv(4096)
                        assert chunk and len(request) + len(chunk) <= 4096
                        request.extend(chunk)
                    if fault == "timeout":
                        assert release.wait(5)
                        return
                    reply = HEAD + TYPE + HTML
                    if fault == "wrong_status":
                        reply = reply.replace(b"413 Too Large", b"200 OK")
                    elif fault == "missing":
                        reply = b""
                    elif fault == "truncated":
                        reply = reply[:-1]
                    elif fault == "missing_length":
                        reply = reply.replace(LENGTH, b"")
                    elif fault == "duplicate_length":
                        reply = reply.replace(LENGTH, LENGTH * 2)
                    connection.sendall(reply)
            except BaseException as error:
                errors.append(error)

        worker = Thread(target=peer, name="synthetic-rejection-peer")
        worker.start()
        try:
            observation = observe_early_response(listener.getsockname()[1],
                b"POST / HTTP/1.0\r\nContent-Length: 1048577\r\n\r\n",
                timeout=0.5 if fault == "timeout" else 5)
            with pytest.raises(AssertionError):
                observation.assert_complete_html(413, ())
            assert observation.supplied_bytes == observation.sent_bytes == 0
            if fault == "wrong_status":
                assert observation.status == 200
                assert observation.receiver_outcome == "complete"
            else:
                assert observation.receiver_outcome == "error"
                assert observation.receiver_error
        finally:
            release.set()
            worker.join(timeout=6)
            assert not worker.is_alive()
        assert errors == []
