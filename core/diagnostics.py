"""Keep interpreter errors separate from program output during verification."""

from contextlib import contextmanager
from contextvars import ContextVar
import sys

_errors = ContextVar('brittainscript_errors', default=None)


def report(message):
    errors = _errors.get()
    if errors is None:
        print(message)
    else:
        errors.append(message)
        print(message, file=sys.stderr)


@contextmanager
def capture_errors():
    errors = []
    token = _errors.set(errors)
    try:
        yield errors
    finally:
        _errors.reset(token)
