"""HTTP client operations using Python's TLS and redirect handling."""

import math
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import json_backend
try:
    from core.values import BSModule
except ModuleNotFoundError:
    from values import BSModule

MAX_RESPONSE_SIZE = 8 * 1024 * 1024
METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')
HEADER_NAME = "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def request(method, url, body=None, headers=None, timeout=10):
    if not isinstance(method, str) or method.upper() not in METHODS:
        raise ValueError('Unsupported HTTP method')
    if not isinstance(url, str):
        raise TypeError('HTTP URL must be a string')
    address = urlsplit(url)
    if address.scheme.lower() not in ('http', 'https') or not address.hostname:
        raise ValueError('HTTP URL must use http:// or https:// with a host')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('HTTP timeout must be a positive finite number of seconds')
    headers = {} if headers is None else headers
    if not isinstance(headers, dict):
        raise TypeError('HTTP headers must be a dictionary')
    outgoing = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise TypeError('HTTP header names and values must be strings')
        if not name or any(char not in HEADER_NAME for char in name):
            raise ValueError('Invalid HTTP header name')
        if '\r' in value or '\n' in value:
            raise ValueError('HTTP headers cannot contain newlines')
        value.encode('latin-1')
        if name.lower() in ('content-length', 'transfer-encoding'):
            raise ValueError('The HTTP client controls transport headers')
        outgoing[name.lower()] = value
    if body is None:
        encoded = None
    elif isinstance(body, str):
        encoded = body.encode('utf-8')
        outgoing.setdefault('content-type', 'text/plain; charset=utf-8')
    elif isinstance(body, bytes):
        encoded = body
        outgoing.setdefault('content-type', 'application/octet-stream')
    else:
        encoded = json_backend.stringify(body).encode('utf-8')
        outgoing.setdefault('content-type', 'application/json')
    outgoing.setdefault('accept', 'application/json')
    outgoing.setdefault('user-agent', 'BrittainScript')
    message = Request(url, data=encoded, headers=outgoing, method=method.upper())
    try:
        response = urlopen(message, timeout=timeout)
    except HTTPError as error:
        # HTTP error statuses are responses. Transport failures still raise.
        response = error
    with response:
        raw = response.read(MAX_RESPONSE_SIZE + 1)
        if len(raw) > MAX_RESPONSE_SIZE:
            raise ValueError('HTTP response body exceeds 8 MiB')
        text = raw.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
        content_type = response.headers.get_content_type()
        data, json_error = None, None
        if raw and (content_type == 'application/json' or (
            content_type.startswith('application/') and content_type.endswith('+json')
        )):
            try:
                data = json_backend.parse(text)
            except ValueError as error:
                json_error = str(error)
        return {'status': response.status if hasattr(response, 'status') else response.code,
                'headers': {name.lower(): value for name, value in response.headers.items()},
                'body': text, 'bytes': raw, 'json': data, 'json_error': json_error,
                'url': response.geturl()}


def create_module():
    funcs = {'request': request}
    for method in METHODS:
        if method in ('POST', 'PUT', 'PATCH'):
            def call(url, body=None, headers=None, timeout=10, method=method):
                return request(method, url, body, headers, timeout)
        else:
            def call(url, headers=None, timeout=10, method=method):
                return request(method, url, None, headers, timeout)
        funcs[method.lower()] = call
    return BSModule({'__bs_module__': True, 'name': 'http', 'funcs': funcs})
