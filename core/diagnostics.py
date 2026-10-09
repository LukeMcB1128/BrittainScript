"""Structured BS errors, source locations, and execution contexts."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import builtins
import sys

_errors = ContextVar('brittainscript_errors', default=None)
_executing = ContextVar('brittainscript_executing', default=False)
_location = ContextVar('brittainscript_location', default=None)
_stack = ContextVar('brittainscript_stack', default=())
_handled = ContextVar('brittainscript_handled', default=None)


@dataclass(frozen=True)
class Frame:
    function: str
    file: str
    line: int
    column: int


class SourceLine(str):
    """A source line retains its location when a block is stored or sliced."""

    def __new__(cls, text, file='<input>', line=1, source=None):
        value = super().__new__(cls, text)
        value.file = file
        value.line = line
        value.source = str(text) if source is None else source
        return value

    def with_text(self, text):
        return SourceLine(text, self.file, self.line, self.source)


def error_types(kind):
    cls = getattr(builtins, kind, None)
    if isinstance(cls, type) and issubclass(cls, Exception):
        return tuple(base.__name__ for base in cls.__mro__) + ('Error',)
    return (kind, 'RuntimeError', 'Exception', 'Error')


class BSError(Exception):
    """The error value visible to BS programs and Python embedding callers."""

    def __init__(self, message, kind='RuntimeError', cause=None, offset=0):
        super().__init__(message)
        self.type = kind
        self.message = message
        self.cause = cause
        self.types = error_types(kind)
        self.stack = list(_stack.get())
        location = _location.get()
        self.file = location[0] if location else '<input>'
        self.line = location[1] if location else 1
        self.column = (location[2] if location else 1) + offset
        self.raised = False

    def __str__(self):
        return self.message

    def __getattr__(self, name):
        # BS fields take precedence. Other attributes retain Python semantics.
        cause = self.__dict__.get('cause')
        if cause is not None:
            return getattr(cause, name)
        raise AttributeError(name)

    def mark_raised(self):
        if not self.raised:
            location = _location.get()
            if location:
                self.file, self.line, self.column = location[:3]
            self.stack = list(_stack.get())
            self.raised = True
        return self

    def matches(self, kind):
        cls = getattr(builtins, kind, None)
        canonical = cls.__name__ if isinstance(cls, type) and issubclass(cls, Exception) else kind
        return canonical in self.types

    def format(self):
        lines = [f'{self.type}: {self.message}',
                 f'  at {self.file}:{self.line}:{self.column}']
        if self.stack:
            lines.append('BS call stack:')
            for frame in self.stack:
                lines.append(f'  {frame.function} at {frame.file}:{frame.line}:{frame.column}')
        return '\n'.join(lines)


def from_python(error):
    if isinstance(error, BSError):
        return error
    result = BSError(str(error), type(error).__name__, error)
    result.args = error.args
    result.raised = True
    result.types = tuple(base.__name__ for base in type(error).__mro__) + ('Error',)
    return result


def infer_type(message):
    if message.startswith(('Syntax error', 'Illegal character')):
        return 'SyntaxError'
    if message.startswith('Undefined'):
        return 'NameError'
    if 'division by zero' in message or 'modulo by zero' in message:
        return 'ZeroDivisionError'
    if 'expects ' in message or 'not callable' in message or 'not iterable' in message:
        return 'TypeError'
    if 'no attribute' in message or 'no method' in message:
        return 'AttributeError'
    if 'empty list' in message:
        return 'IndexError'
    return 'RuntimeError'


def report(message, kind=None, cause=None, offset=0):
    # Direct parser users retain the old diagnostic interface. Executed BS
    # programs raise, so a failed expression cannot produce a value.
    if _executing.get():
        if isinstance(cause, BSError):
            raise cause
        detail = str(cause) if cause is not None else message
        if cause is None:
            for prefix in ('Error: ', 'GUI error: ', 'Syntax error: '):
                if detail.startswith(prefix):
                    detail = detail[len(prefix):]
                    break
        error = BSError(detail, kind or (type(cause).__name__ if cause is not None else infer_type(message)),
                        cause, offset)
        error.raised = True
        if cause is not None:
            error.args = cause.args
            error.types = tuple(base.__name__ for base in type(cause).__mro__) + ('Error',)
        raise error from cause
    errors = _errors.get()
    if errors is None:
        print(message)
    else:
        errors.append(message)
        print(message, file=sys.stderr)


def emit(error):
    errors = _errors.get()
    if errors is not None:
        errors.append(error)
    print(error.format(), file=sys.stderr)


@contextmanager
def execution():
    token = _executing.set(True)
    try:
        yield
    finally:
        _executing.reset(token)


@contextmanager
def source_location(source):
    column = len(source.source) - len(source.source.lstrip(' \t')) + 1
    token = _location.set((source.file, source.line, column, str(source).lstrip(' \t')))
    try:
        yield
    finally:
        _location.reset(token)


@contextmanager
def expression_location(text):
    location = _location.get()
    token = None
    if location:
        index = location[3].rfind(text)
        if index >= 0:
            token = _location.set((location[0], location[1], location[2] + index, location[3]))
    try:
        yield
    finally:
        if token is not None:
            _location.reset(token)


@contextmanager
def expression_offset(offset):
    location = _location.get()
    token = None
    if location:
        token = _location.set((location[0], location[1], location[2] + offset, location[3]))
    try:
        yield
    finally:
        if token is not None:
            _location.reset(token)


@contextmanager
def call_frame(name):
    location = _location.get() or ('<input>', 1, 1, '')
    token = _stack.set(_stack.get() + (Frame(name, *location[:3]),))
    try:
        yield
    finally:
        _stack.reset(token)


@contextmanager
def handling(error):
    token = _handled.set(error)
    try:
        yield
    finally:
        _handled.reset(token)


def current_error():
    return _handled.get()


@contextmanager
def capture_errors():
    errors = []
    token = _errors.set(errors)
    try:
        yield errors
    finally:
        _errors.reset(token)
