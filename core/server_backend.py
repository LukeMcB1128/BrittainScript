"""Native BS request handlers served through Werkzeug and Waitress."""

from dataclasses import dataclass
import ipaddress
import threading
import time

import json_backend
try:
    import core.diagnostics as diagnostics
    import core.runtime as runtime
    from core.values import BSModule
except ModuleNotFoundError:
    import diagnostics
    import runtime
    from values import BSModule

MAX_BODY_SIZE = 1024 * 1024
METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')
INSTALL_HINT = "Install server support: python3 -m pip install 'brittainscript[server]'"


@dataclass(frozen=True)
class ResponseValue:
    body: object
    status: int
    headers: dict


class Server:
    def __init__(self, interpreter):
        try:
            from werkzeug.wrappers import Request, Response
            from werkzeug.routing import Map, Rule
            from werkzeug.exceptions import HTTPException, MethodNotAllowed, BadRequest
        except ImportError as error:
            raise ImportError(INSTALL_HINT) from error
        self.interpreter = interpreter
        self.Request, self.Response = Request, Response
        self.Rule = Rule
        self.HTTPException, self.MethodNotAllowed, self.BadRequest = HTTPException, MethodNotAllowed, BadRequest
        self.routes = Map()
        self.registered = set()
        self.template = None
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.backend = None
        self.running = False

    def route(self, method, path, handler):
        if not isinstance(method, str) or method.upper() not in METHODS:
            raise ValueError('Unsupported HTTP method')
        method = method.upper()
        if not isinstance(path, str) or not path.startswith('/'):
            raise ValueError('Route paths must start with /')
        definition = self.interpreter.current_functions().get(handler) if isinstance(handler, str) else None
        if definition is None:
            raise ValueError('The handler must name an existing BS function')
        if len(definition[0]) != 1:
            raise ValueError('A request handler must have one parameter')
        with self.lock:
            if self.template is not None:
                raise RuntimeError('Register routes before server.app() or server.run()')
            if (method, path) in self.registered or (
                method in ('GET', 'HEAD') and
                ({('GET', path), ('HEAD', path)} & self.registered)
            ):
                raise ValueError('This HTTP method and route are already registered')
            # Werkzeug adds HEAD to GET routes and checks converter syntax here.
            self.routes.add(self.Rule(path, methods=[method], endpoint=handler))
            self.registered.add((method, path))
        return True

    def app(self):
        with self.lock:
            if self.template is None:
                self.routes.update()
                globals_ = self.interpreter.parser_module.current_scopes()[0]
                self.template = runtime.Runtime([runtime.clone(globals_)],
                                                dict(self.interpreter.current_functions()))
        return self

    def response(self, body, status=200, headers=None):
        if type(status) is not int or not 200 <= status <= 599:
            raise ValueError('Response status must be an integer from 200 to 599')
        headers = {} if headers is None else headers
        if not isinstance(headers, dict):
            raise TypeError('Response headers must be a dictionary')
        for name, value in headers.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise TypeError('Response header names and values must be strings')
            if not name or any(char not in "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" for char in name):
                raise ValueError('Invalid response header name')
            if '\r' in value or '\n' in value:
                raise ValueError('Response headers cannot contain newlines')
            if name.lower() in ('content-length', 'transfer-encoding', 'connection'):
                raise ValueError('The HTTP backend controls transport headers')
        return ResponseValue(body, status, dict(headers))

    def _response(self, value):
        if isinstance(value, ResponseValue):
            body, status, headers = value.body, value.status, value.headers
        else:
            body, status, headers = value, 200, {}
        if isinstance(body, str):
            response = self.Response(body, status=status, content_type='text/plain; charset=utf-8')
        elif isinstance(body, bytes):
            response = self.Response(body, status=status, content_type='application/octet-stream')
        else:
            response = self.Response(json_backend.stringify(body), status=status, content_type='application/json')
        response.headers.update(headers)
        return response

    def _error(self, status, message, headers=None):
        return self._response(self.response({'error': message}, status, headers))

    def _request(self, request, params):
        request.max_content_length = MAX_BODY_SIZE
        try:
            body = request.get_data().decode('utf-8')
            is_json = request.mimetype == 'application/json' or (
                request.mimetype.startswith('application/') and request.mimetype.endswith('+json'))
            data = json_backend.parse(body) if is_json else None
        except (UnicodeError, ValueError) as error:
            raise self.BadRequest('The request body must contain valid UTF-8 and JSON') from error
        return {'method': request.method, 'path': request.path, 'params': params,
                'query': request.args.to_dict(), 'query_all': request.args.to_dict(flat=False),
                'headers': {name.lower(): value for name, value in request.headers.items()},
                'body': body, 'json': data}

    def __call__(self, environ, start_response):
        self.app()
        request = self.Request(environ)
        if self.stopping.is_set():
            return self._error(503, 'Server is stopping')(environ, start_response)
        try:
            handler, params = self.routes.bind_to_environ(environ).match()
            data = self._request(request, params)
            state = runtime.Runtime([runtime.clone(self.template.scopes[0])], dict(self.template.functions))
            source = diagnostics.SourceLine('', file=f'<HTTP {request.method} {request.path}>')
            with runtime.activate(state), diagnostics.execution(), diagnostics.source_location(source):
                value = self.interpreter.call_user_function(handler, [data])
                response = self._response(value)
        except self.HTTPException as error:
            headers = {name: value for name, value in error.get_response(environ).headers.items()
                       if name.lower() not in ('content-type', 'content-length')}
            if isinstance(error, self.MethodNotAllowed) and request.method == 'OPTIONS':
                headers['Allow'] = ', '.join(sorted(set(error.valid_methods) | {'OPTIONS'}))
                response = self._response(self.response('', 204, headers))
            else:
                response = self._error(error.code, error.name, headers)
        except Exception as error:
            diagnostics.emit(diagnostics.from_python(error))
            response = self._error(500, 'Internal server error')
        return response(environ, start_response)

    def port(self):
        with self.lock:
            return int(self.backend.effective_port) if self.backend is not None else None

    def stop(self):
        with self.lock:
            if self.backend is None:
                return False
            self.stopping.set()
            self.backend.pull_trigger()
            return True

    def run(self, host='127.0.0.1', port=8000):
        if not isinstance(host, str):
            raise TypeError('Server host must be an IP address string')
        address = ipaddress.ip_address(host)
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError('Server port must be an integer from 0 to 65535')
        try:
            from waitress.server import create_server
            from waitress.task import ThreadedTaskDispatcher
        except ImportError as error:
            raise ImportError(INSTALL_HINT) from error
        with self.lock:
            if self.running:
                raise RuntimeError('This server is already running')
            self.running = True
            self.stopping.clear()
        connections = {}
        dispatcher = ThreadedTaskDispatcher()
        backend = None
        try:
            self.app()
            dispatcher.set_thread_count(4)
            backend = create_server(self, map=connections, _dispatcher=dispatcher,
                                    host=host, port=port, ipv4=address.version == 4,
                                    ipv6=address.version == 6, max_request_body_size=MAX_BODY_SIZE)
            with self.lock:
                self.backend = backend
            deadline = None
            while True:
                try:
                    backend.asyncore.loop(timeout=0.05, count=1, map=connections)
                except KeyboardInterrupt:
                    self.stop()
                if self.stopping.is_set():
                    deadline = deadline or time.monotonic() + 5
                    active = any(getattr(channel, 'requests', None) or
                                 getattr(channel, 'total_outbufs_len', 0)
                                 for channel in list(connections.values()))
                    if not active or time.monotonic() >= deadline:
                        break
        finally:
            dispatcher.shutdown(timeout=5)
            for channel in list(connections.values()):
                channel.close()
            with self.lock:
                self.backend = None
                self.running = False
        return True


def create_module(interpreter):
    server = Server(interpreter)
    funcs = {name: getattr(server, name) for name in ('route', 'response', 'app', 'run', 'stop', 'port')}
    for method in METHODS:
        funcs[method.lower()] = lambda path, handler, method=method: server.route(method, path, handler)
    return BSModule({'__bs_module__': True, 'name': 'server', 'funcs': funcs})
