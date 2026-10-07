"""JSON dictionaries with locked transactions and atomic file replacement."""

from contextlib import contextmanager
import os
from pathlib import Path
import stat
import tempfile
import threading

import json_backend
try:
    import core.runtime as runtime
    from core.values import BSModule
except ModuleNotFoundError:
    import runtime
    from values import BSModule

_registry_lock = threading.Lock()
_locks = {}
_transactions = threading.local()


@contextmanager
def file_lock(path):
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b'\0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_save(path, value):
    text = json_backend.stringify(value)
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as target:
            if path.exists():
                os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            target.write(text)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class Store:
    def __init__(self, path, interpreter):
        self.path = Path(path).expanduser().resolve()
        self.lock_path = self.path.with_name(self.path.name + '.lock')
        self.interpreter = interpreter
        with _registry_lock:
            self.lock = _locks.setdefault(str(self.path), threading.RLock())
        with self._locked():
            if self.path.exists():
                self._read()
            else:
                atomic_save(self.path, {})

    @contextmanager
    def _locked(self):
        if getattr(_transactions, 'active', False):
            raise RuntimeError('A store transaction callback must not call store methods')
        with self.lock, file_lock(self.lock_path):
            _transactions.active = True
            try:
                yield
            finally:
                _transactions.active = False

    def _read(self):
        value = json_backend.load(self.path)
        if not isinstance(value, dict):
            raise ValueError('A store file must contain a JSON object')
        return value

    def _key(self, key):
        if not isinstance(key, str):
            raise TypeError('Store keys must be strings')

    def get(self, key, default=None):
        self._key(key)
        with self._locked():
            return runtime.clone(self._read().get(key, default))

    def set(self, key, value):
        self._key(key)
        json_backend._validate(value)
        with self._locked():
            data = self._read()
            data[key] = value
            atomic_save(self.path, data)
        return True

    def has(self, key):
        self._key(key)
        with self._locked():
            return key in self._read()

    def delete(self, key):
        self._key(key)
        with self._locked():
            data = self._read()
            if key not in data:
                return False
            del data[key]
            atomic_save(self.path, data)
        return True

    def keys(self):
        with self._locked():
            return list(self._read())

    def snapshot(self):
        with self._locked():
            return self._read()

    def _callback(self, callback, value, args):
        args = [] if args is None else args
        if not isinstance(args, list):
            raise TypeError('Store callback arguments must be a list')
        definition = self.interpreter.current_functions().get(callback) if isinstance(callback, str) else None
        if definition is None or len(definition[0]) != 1 + len(args):
            raise ValueError('Store callback must name a BS function with one value parameter plus its supplied arguments')
        state = runtime.Runtime([runtime.clone(self.interpreter.parser_module.current_scopes()[0])],
                                dict(self.interpreter.current_functions()))
        with runtime.activate(state):
            return self.interpreter.call_definition(callback, definition, [value, *runtime.clone(args)])

    def update(self, key, callback, default=None, args=None):
        self._key(key)
        with self._locked():
            data = self._read()
            value = self._callback(callback, runtime.clone(data.get(key, default)), args)
            data[key] = value
            atomic_save(self.path, data)
            return runtime.clone(value)

    def transaction(self, callback, args=None):
        with self._locked():
            data = self._callback(callback, self._read(), args)
            if not isinstance(data, dict):
                raise TypeError('A store transaction must return a dictionary')
            atomic_save(self.path, data)
            return runtime.clone(data)


def create_module(interpreter):
    def open_store(path):
        if not isinstance(path, str):
            raise TypeError('Store path must be a string')
        return Store(path, interpreter)
    return BSModule({'__bs_module__': True, 'name': 'store', 'funcs': {'open': open_store}})
