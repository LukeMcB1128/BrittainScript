"""Build expression trees before evaluating any operation or function call."""

from functools import wraps
from threading import RLock
try:
    from core.diagnostics import BSError, report, expression_offset
    from core.strings import ExpressionText, CompiledPart, StringTemplate
except ModuleNotFoundError:
    from diagnostics import BSError, report, expression_offset
    from strings import ExpressionText, CompiledPart, StringTemplate


def evaluate(value):
    if isinstance(value, Reduction):
        return value.evaluate()
    if isinstance(value, list):
        return [evaluate(item) for item in value]
    if isinstance(value, tuple):
        return tuple(evaluate(item) for item in value)
    return value


def validate_calls(value, argument=False):
    """Reject assignment syntax in call arguments before any expression runs."""
    if isinstance(value, Reduction):
        name = value.action.__name__
        if argument and name == 'p_statement_assign':
            report('Keyword arguments are not supported; use positional arguments',
                   kind='TypeError', offset=value.positions[2])
            return False
        argument_index = {'p_expression_function_call': 3,
                          'p_expression_range_call': 3,
                          'p_expression_method_call': 5}.get(name)
        return all(validate_calls(child, argument or index == argument_index)
                   for index, child in enumerate(value.values[1:], 1))
    if isinstance(value, (list, tuple)):
        return all(validate_calls(child, argument) for child in value)
    return True


class InvalidTemplate(Exception):
    """Stop evaluation after a low-level parser diagnostic without raising BS errors."""


def compile_templates(value, parser):
    if isinstance(value, Reduction):
        value.values = [compile_templates(child, parser) for child in value.values]
    elif isinstance(value, StringTemplate):
        import lexer
        parts = []
        for part in value.parts:
            if isinstance(part, ExpressionText):
                with expression_offset(part.offset):
                    tree = parser.compile(part.text, lexer=lexer.lexer.clone())
                    if tree is None:
                        raise InvalidTemplate()
                    if contains_assignment(tree):
                        report('Assignments are not allowed in interpolation', kind='SyntaxError')
                        raise InvalidTemplate()
                parts.append(CompiledPart(tree, part.offset))
            else:
                parts.append(part)
        return StringTemplate(tuple(parts))
    elif isinstance(value, list):
        return [compile_templates(child, parser) for child in value]
    elif isinstance(value, tuple):
        return tuple(compile_templates(child, parser) for child in value)
    return value


def contains_assignment(value):
    if isinstance(value, Reduction):
        return value.action.__name__ == 'p_statement_assign' or any(contains_assignment(child) for child in value.values)
    if isinstance(value, (list, tuple)):
        return any(contains_assignment(child) for child in value)
    return False


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
            if name == 'p_expression_interpolated':
                parts = []
                for part in self.values[1].parts:
                    if isinstance(part, CompiledPart):
                        with expression_offset(part.offset):
                            value = evaluate(part.tree)
                        parts.append('null' if value is None else str(value))
                    else:
                        parts.append(part)
                return ''.join(parts)
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
            tree = self.grammar.parse(*args, **kwargs)
        try:
            tree = compile_templates(tree, self)
        except InvalidTemplate:
            return None
        return tree if validate_calls(tree) else None

    def parse(self, *args, **kwargs):
        return evaluate(self.compile(*args, **kwargs))
