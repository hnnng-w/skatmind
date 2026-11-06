"""Invocation-local observation of genuine public execution, without a public option."""

from contextlib import contextmanager
from contextvars import ContextVar

_OBSERVER = ContextVar("skatmind_private_execution_observer", default=None)


@contextmanager
def capture_native_execution():
    values = []
    token = _OBSERVER.set(values)
    try:
        yield values
    finally:
        _OBSERVER.reset(token)


def observe_native_execution(invocation, execution, public_result):
    values = _OBSERVER.get()
    if values is not None:
        values.append((invocation, execution, public_result))
