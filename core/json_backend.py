"""JSON operations shared by BS libraries and HTTP request handling."""

import json
import math
import os


def _reject_constant(value):
    raise ValueError(f'{value} is not a valid JSON number')


def parse(text):
    if not isinstance(text, str):
        raise TypeError('JSON input must be a string')
    value = json.loads(text, parse_constant=_reject_constant)
    _validate(value)
    return value


def _validate(value, active=None):
    active = set() if active is None else active
    if isinstance(value, str):
        value.encode('utf-8')
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('JSON numbers must be finite')
        return
    if not isinstance(value, (dict, list)):
        raise TypeError(f'{type(value).__name__} is not a JSON value')
    if id(value) in active:
        raise ValueError('JSON data contains a cycle')
    active.add(id(value))
    try:
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError('JSON object keys must be strings')
                key.encode('utf-8')
                _validate(item, active)
        else:
            for item in value:
                _validate(item, active)
    finally:
        active.remove(id(value))


def stringify(value, indent=None):
    if indent is not None and (type(indent) is not int or indent < 0):
        raise ValueError('JSON indentation must be a non-negative integer')
    _validate(value)
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=indent,
                      separators=(',', ':') if indent is None else None)


def load(path):
    with open(os.fspath(path), encoding='utf-8') as source:
        return parse(source.read())


def save(path, value):
    # Validate before opening the destination, so invalid data cannot erase it.
    text = stringify(value)
    with open(os.fspath(path), 'w', encoding='utf-8') as destination:
        destination.write(text)
    return True


BUILTINS = {
    'jsonparse': parse,
    'jsonstringify': stringify,
    'jsonload': load,
    'jsonsave': save,
}
