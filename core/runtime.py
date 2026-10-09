"""Separate interpreter state for independent executions such as HTTP requests."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
try:
    from core.values import BSModule
except ModuleNotFoundError:
    from values import BSModule

state = ContextVar('brittainscript_runtime', default=None)


@dataclass
class Runtime:
    scopes: list
    functions: dict
    environments: list = field(default_factory=lambda: [None])


@contextmanager
def activate(runtime):
    token = state.set(runtime)
    try:
        yield
    finally:
        state.reset(token)


def clone(value, memo=None):
    """Copy BS containers and their aliases; retain opaque Python values."""
    memo = {} if memo is None else memo
    if id(value) in memo:
        return memo[id(value)]
    if isinstance(value, dict):
        result = BSModule() if isinstance(value, BSModule) else {}
        memo[id(value)] = result
        for key, item in value.items():
            result[key] = clone(item, memo)
        return result
    if isinstance(value, list):
        result = []
        memo[id(value)] = result
        result.extend(clone(item, memo) for item in value)
        return result
    # Function definitions contain immutable parameter/source metadata in tuples.
    # Opaque Python objects may hold locks or connections and remain shared.
    return value
