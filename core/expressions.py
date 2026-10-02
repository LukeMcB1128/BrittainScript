"""Build expression trees before evaluating any operation or function call."""

from functools import wraps
from threading import RLock
try:
    from core.diagnostics import BSError, report
except ModuleNotFoundError:
    from diagnostics import BSError, report


def evaluate(value):
    if isinstance(value, Reduction):
        return value.evaluate()
    if isinstance(value, list):
        return [evaluate(item) for item in value]
    if isinstance(value, tuple):
        return tuple(evaluate(item) for item in value)
    return value


class EvaluationSlice:
    """The reduction interface used by the existing expression operations."""

    def __init__(self, node):
        self.values = [None] + [evaluate(value) for value in node.values[1:]]
        self.positions = node.positions

    def __getitem__(self, index):
        return self.values[index]

    def __setitem__(self, index, value):
        self.values[index] = value

    def lexpos(self, index):
        return self.positions[index]


class Reduction:
    """An expression node with unevaluated children and token positions."""

    def __init__(self, action, production):
        self.action = action
        self.values = [None] + [production[index] for index in range(1, len(production))]
        self.positions = [production.lexpos(index) for index in range(len(production))]

    def evaluate(self):
        try:
            name = self.action.__name__
            if name == 'p_expression_and':
                return bool(evaluate(self.values[1])) and bool(evaluate(self.values[3]))
            if name == 'p_expression_or':
                return bool(evaluate(self.values[1])) or bool(evaluate(self.values[3]))
            if name == 'p_expression_dictionary':
                result = {}
                for key, value in self.values[2]:
                    key = evaluate(key)
                    value = evaluate(value)
                    result[key] = value
                return result
            production = EvaluationSlice(self)
            self.action(production)
            return production[0]
        except BSError:
            raise
        except Exception as error:
            offset = self.positions[2] if len(self.positions) > 2 else self.positions[1]
            report('Error evaluating expression', cause=error, offset=offset)
            return None


def deferred(action):
    @wraps(action)
    def build(production):
        production[0] = Reduction(action, production)
    return build


class ExpressionParser:
    """Keep parser.parse() compatible while separating parsing and execution."""

    def __init__(self, grammar):
        self.grammar = grammar
        self.lock = RLock()

    def compile(self, *args, **kwargs):
        with self.lock:
            return self.grammar.parse(*args, **kwargs)

    def parse(self, *args, **kwargs):
        return evaluate(self.compile(*args, **kwargs))
