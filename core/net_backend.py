"""Socket primitives for BS libraries such as web.bs and ui.bs.

Everything here uses the Python standard library only. The HTTP protocol,
routing and the UI framework are written in BrittainScript on top of these.

Sockets are handed to BS code as integer handles. Network data crosses into
BS as "raw" strings where each character is one byte (latin-1), so lengths
match byte counts; encode()/decode() convert between raw strings and text.
"""

import math
import os
import secrets
import selectors
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

try:
    from core.values import BSModule
except ModuleNotFoundError:
    from values import BSModule

RECV_TIMEOUT = 5
IDLE_LIMIT = 30

sockets = {}
listeners = {}  # listener handle -> {handle: accepted time} of connections not yet readable
next_handle = 1


def _register(sock):
    global next_handle
    handle = next_handle
    next_handle += 1
    sockets[handle] = sock
    return handle


def _socket(handle):
    sock = sockets.get(handle)
    if sock is None:
        raise ValueError(f'No open socket with handle {handle}')
    return sock


def _seconds(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be a non-negative number of seconds')
    return value


def listen(host='127.0.0.1', port=0):
    if not isinstance(host, str):
        raise TypeError('Host must be a string')
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Port must be an integer from 0 to 65535')
    family = socket.AF_INET6 if ':' in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(64)
    except Exception:
        sock.close()
        raise
    sock.setblocking(False)
    handle = _register(sock)
    listeners[handle] = {}
    return handle


def port(handle):
    return _socket(handle).getsockname()[1]


def wait(handle, timeout=1):
    """Return a connection with request data ready to read, or null on timeout.

    New connections are accepted in the background of this call and only
    handed out once they have data, so idle browser preconnects never block
    a single-threaded BS server.
    """
    server = _socket(handle)
    if handle not in listeners:
        raise ValueError('wait() needs a listening socket')
    pending = listeners[handle]
    deadline = time.monotonic() + _seconds(timeout, 'Timeout')
    while True:
        now = time.monotonic()
        for conn_handle, accepted in list(pending.items()):
            if now - accepted > IDLE_LIMIT:
                close(conn_handle)
        with selectors.DefaultSelector() as selector:
            selector.register(server, selectors.EVENT_READ, None)
            for conn_handle in pending:
                selector.register(sockets[conn_handle], selectors.EVENT_READ, conn_handle)
            events = selector.select(max(0, deadline - now))
        for key, _ in events:
            if key.data is None:
                try:
                    conn, _ = server.accept()
                except (BlockingIOError, InterruptedError):
                    continue
                conn.setblocking(True)
                pending[_register(conn)] = time.monotonic()
            else:
                del pending[key.data]
                return key.data
        if time.monotonic() >= deadline:
            return None


def recv(handle, size=65536):
    if type(size) is not int or size <= 0:
        raise ValueError('Receive size must be a positive integer')
    sock = _socket(handle)
    sock.settimeout(RECV_TIMEOUT)
    return sock.recv(size).decode('latin-1')


def send(handle, raw):
    if not isinstance(raw, str):
        raise TypeError('send() expects a raw string; use net.encode(text) first')
    _socket(handle).sendall(raw.encode('latin-1'))
    return len(raw)


def close(handle):
    sock = sockets.pop(handle, None)
    if sock is None:
        return False
    for pending in listeners.values():
        pending.pop(handle, None)
    for conn_handle in list(listeners.pop(handle, {})):
        close(conn_handle)
    try:
        sock.close()
    except OSError:
        pass
    return True


def encode(text):
    if not isinstance(text, str):
        raise TypeError('encode() expects a string')
    return text.encode('utf-8').decode('latin-1')


def decode(raw):
    if not isinstance(raw, str):
        raise TypeError('decode() expects a raw string')
    return raw.encode('latin-1').decode('utf-8', errors='replace')


def clock():
    return time.monotonic()


def sleep(seconds):
    time.sleep(_seconds(seconds, 'Sleep time'))
    return None


def token():
    return secrets.token_hex(16)


def _app_browsers():
    if sys.platform == 'darwin':
        for name in ('Google Chrome', 'Microsoft Edge', 'Chromium', 'Brave Browser'):
            for root in ('/Applications', os.path.expanduser('~/Applications')):
                if os.path.isdir(os.path.join(root, name + '.app')):
                    yield ['open', '-na', name, '--args']
                    break
    elif os.name == 'nt':
        roots = [os.environ.get(key) for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA')]
        paths = (r'Google\Chrome\Application\chrome.exe', r'Microsoft\Edge\Application\msedge.exe',
                 r'BraveSoftware\Brave-Browser\Application\brave.exe')
        for path in paths:
            for root in roots:
                if root and os.path.isfile(os.path.join(root, path)):
                    yield [os.path.join(root, path)]
                    break
    else:
        for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser',
                     'microsoft-edge', 'brave-browser'):
            found = shutil.which(name)
            if found:
                yield [found]


def open_app(url, width=1000, height=720):
    """Open url in a chromeless app window, or a normal browser tab as a fallback.

    Returns true when an app window was launched.
    """
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        raise ValueError('open_app() expects an http:// or https:// URL')
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError('Window width and height must be positive integers')
    # BS_UI_BROWSER=tab skips app windows; BS_UI_BROWSER=none opens nothing (tests, remote use).
    mode = os.environ.get('BS_UI_BROWSER', '')
    if mode == 'none':
        return False
    if mode != 'tab':
        for command in _app_browsers():
            try:
                subprocess.Popen(command + [f'--app={url}', f'--window-size={width},{height}'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except OSError:
                continue
    webbrowser.open(url)
    return False


def create_module():
    funcs = {
        'listen': listen, 'port': port, 'wait': wait, 'recv': recv, 'send': send,
        'close': close, 'encode': encode, 'decode': decode, 'clock': clock,
        'sleep': sleep, 'token': token, 'openApp': open_app,
    }
    return BSModule({'__bs_module__': True, 'name': 'net', 'funcs': funcs})
