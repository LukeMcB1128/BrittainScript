"""Parse Python and reject anything outside the translatable subset.

Everything here runs before a single line is emitted, so a rejection names the
feature and the line rather than producing BrittainScript that quietly means
something else.
"""

import ast
import warnings

from .errors import UnsupportedFeature

# builtins with an exact BrittainScript equivalent
CALLABLE_BUILTINS = {
    'print': 'push',
    'len': 'len',
    'str': 'tostr',
    'abs': 'absolute',
    'round': 'round',
}

# range() maps to space(), but only as a for-loop iterable: space() builds a
# list, so printing one or holding it in a variable would not match Python
ITERABLE_ONLY_BUILTINS = {'range': 'space'}

# methods that behave identically in both languages. Others are rejected by
# name: list.pop() in particular returns the popped item in Python but null in
# BrittainScript, which would be a silent wrong answer.
ALLOWED_METHODS = {
    'append', 'upper', 'lower', 'strip', 'find', 'replace', 'split', 'count',
    'join', 'startswith', 'endswith', 'index', 'insert', 'extend', 'reverse',
    'sort', 'remove',
}

REJECTED_METHODS = {
    'pop': 'list.pop() returns the item in Python but null in BrittainScript',
}

BINARY_OPERATORS = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Mod: '%',
}

REJECTED_BINARY_OPERATORS = {
    ast.Pow: ('power operator', "'**' yields an int in Python but a float in BrittainScript"),
    ast.MatMult: ('matrix multiply', 'needs an imported library'),
    ast.BitOr: ('bitwise operators', None),
    ast.BitAnd: ('bitwise operators', None),
    ast.BitXor: ('bitwise operators', None),
    ast.LShift: ('bitwise operators', None),
    ast.RShift: ('bitwise operators', None),
}

COMPARISON_OPERATORS = {
    ast.Eq: '==',
    ast.NotEq: '!=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.Gt: '>',
    ast.GtE: '>=',
}


def is_boolean_valued(node):
    # BrittainScript's 'and'/'or' return a bool, where Python returns one of the
    # operands. They only agree when both sides are already booleans.
    if isinstance(node, ast.Compare):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return True
    if isinstance(node, ast.BoolOp):
        return all(is_boolean_valued(value) for value in node.values)
    return False


def is_total_and_pure(node):
    # BrittainScript evaluates both sides of 'and'/'or', so the right-hand side
    # must not be able to fail or have an effect. This is what makes the common
    # guard 'i < len(xs) and xs[i] > 0' unsafe to translate.
    for child in ast.walk(node):
        if isinstance(child, (ast.Call, ast.Subscript, ast.Attribute)):
            return False
        if isinstance(child, ast.BinOp) and isinstance(child.op, (ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)):
            return False
    return True


class CapabilityValidator(ast.NodeVisitor):
    def __init__(self):
        self.function_names = set()
        self.function_depth = 0

    def reject(self, node, feature, detail=None):
        raise UnsupportedFeature(feature, getattr(node, 'lineno', None), detail)

    # --- wholly unsupported statements -----------------------------------
    def visit_ClassDef(self, node):
        self.reject(node, 'classes')

    def visit_Import(self, node):
        self.reject(node, 'imports')

    def visit_ImportFrom(self, node):
        self.reject(node, 'imports')

    def visit_Try(self, node):
        self.reject(node, 'try/except')

    def visit_TryStar(self, node):
        self.reject(node, 'try/except')

    def visit_With(self, node):
        self.reject(node, 'with')

    def visit_AsyncWith(self, node):
        self.reject(node, 'async')

    def visit_AsyncFor(self, node):
        self.reject(node, 'async')

    def visit_AsyncFunctionDef(self, node):
        self.reject(node, 'async')

    def visit_Global(self, node):
        self.reject(node, 'global/nonlocal')

    def visit_Nonlocal(self, node):
        self.reject(node, 'global/nonlocal')

    def visit_Raise(self, node):
        self.reject(node, 'raise')

    def visit_Assert(self, node):
        self.reject(node, 'assert')

    def visit_Delete(self, node):
        self.reject(node, 'del')

    def visit_AnnAssign(self, node):
        self.reject(node, 'annotated assignment')

    def visit_Lambda(self, node):
        self.reject(node, 'lambda')

    def visit_ListComp(self, node):
        self.reject(node, 'comprehensions')

    def visit_SetComp(self, node):
        self.reject(node, 'comprehensions')

    def visit_DictComp(self, node):
        self.reject(node, 'comprehensions')

    def visit_GeneratorExp(self, node):
        self.reject(node, 'comprehensions')

    def visit_Yield(self, node):
        self.reject(node, 'generators')

    def visit_YieldFrom(self, node):
        self.reject(node, 'generators')

    def visit_Dict(self, node):
        self.reject(node, 'dict literals')

    def visit_Set(self, node):
        self.reject(node, 'set literals')

    def visit_Tuple(self, node):
        self.reject(node, 'tuples')

    def visit_Starred(self, node):
        self.reject(node, 'star unpacking')

    def visit_IfExp(self, node):
        self.reject(node, 'conditional expression')

    def visit_JoinedStr(self, node):
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                if value.format_spec is not None or value.conversion not in (-1, None):
                    self.reject(node, 'format specifiers')
        self.generic_visit(node)

    # --- partially supported ---------------------------------------------
    def visit_FunctionDef(self, node):
        if node.decorator_list:
            self.reject(node, 'decorators')
        arguments = node.args
        if arguments.vararg or arguments.kwarg:
            self.reject(node, 'star arguments')
        if arguments.kwonlyargs or arguments.posonlyargs:
            self.reject(node, 'keyword-only arguments')
        if arguments.defaults or arguments.kw_defaults:
            self.reject(node, 'default arguments')
        if self.function_depth:
            self.reject(node, 'nested functions')
        self.function_names.add(node.name)
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    def visit_Assign(self, node):
        if len(node.targets) != 1:
            self.reject(node, 'multiple assignment')
        target = node.targets[0]
        if isinstance(target, (ast.Tuple, ast.List)):
            self.reject(node, 'tuple unpacking')
        if not isinstance(target, (ast.Name, ast.Subscript)):
            self.reject(node, 'assignment target')
        self.generic_visit(node)

    def visit_For(self, node):
        if node.orelse:
            self.reject(node, 'loop else')
        if not isinstance(node.target, ast.Name):
            self.reject(node, 'tuple unpacking')
        # range() is allowed here and nowhere else, so check its arguments
        # directly rather than letting visit_Call reject the call itself
        if is_range_call(node.iter):
            if len(node.iter.args) not in (1, 2, 3):
                self.reject(node, 'range() arity')
            for argument in node.iter.args:
                self.visit(argument)
        else:
            self.visit(node.iter)
        self.visit(node.target)
        for statement in node.body:
            self.visit(statement)

    def visit_AugAssign(self, node):
        if not isinstance(node.target, (ast.Name, ast.Subscript)):
            self.reject(node, 'assignment target')
        for operator_type, (feature, detail) in REJECTED_BINARY_OPERATORS.items():
            if isinstance(node.op, operator_type):
                self.reject(node, feature, detail)
        if type(node.op) not in BINARY_OPERATORS:
            self.reject(node, 'operator', type(node.op).__name__)
        self.generic_visit(node)

    def visit_While(self, node):
        if node.orelse:
            self.reject(node, 'loop else')
        self.generic_visit(node)

    def visit_BinOp(self, node):
        for operator_type, (feature, detail) in REJECTED_BINARY_OPERATORS.items():
            if isinstance(node.op, operator_type):
                self.reject(node, feature, detail)
        if type(node.op) not in BINARY_OPERATORS and not isinstance(node.op, ast.FloorDiv):
            self.reject(node, 'operator', type(node.op).__name__)
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Invert):
            self.reject(node, 'bitwise operators')
        self.generic_visit(node)

    def visit_Compare(self, node):
        if len(node.ops) != 1:
            self.reject(node, 'chained comparison')
        operator = node.ops[0]
        if isinstance(operator, (ast.In, ast.NotIn)):
            self.reject(node, 'in operator')
        if isinstance(operator, (ast.Is, ast.IsNot)):
            self.reject(node, 'is operator')
        if type(operator) not in COMPARISON_OPERATORS:
            self.reject(node, 'comparison', type(operator).__name__)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # both operands are evaluated in BrittainScript, and the result is a
        # bool rather than one of the operands
        if not is_boolean_valued(node):
            self.reject(
                node,
                'non-boolean and/or',
                "'and'/'or' return a bool in BrittainScript, not the operand",
            )
        for value in node.values[1:]:
            if not is_total_and_pure(value):
                self.reject(
                    node,
                    'short-circuit and/or',
                    'BrittainScript evaluates both sides, so this cannot guard',
                )
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Slice):
            if node.slice.step is not None:
                self.reject(node, 'slice step')
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # only method calls are reachable; a bare attribute is rejected here
        self.reject(node, 'attribute access')

    def visit_Call(self, node):
        if node.keywords:
            self.reject(node, 'keyword arguments')
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
            if name in REJECTED_METHODS:
                self.reject(node, f'{name}() method', REJECTED_METHODS[name])
            if name not in ALLOWED_METHODS:
                self.reject(node, 'unsupported method', f'{name}()')
            self.visit(node.func.value)
            for argument in node.args:
                self.visit(argument)
            return
        if not isinstance(node.func, ast.Name):
            self.reject(node, 'computed call')
        name = node.func.id
        if name in ITERABLE_ONLY_BUILTINS:
            self.reject(node, f'{name}() outside a for loop')
        if name in ('open', 'input', 'eval', 'exec', '__import__'):
            self.reject(node, 'I/O or dynamic execution', f'{name}()')
        if name not in CALLABLE_BUILTINS and name not in self.function_names:
            self.reject(node, 'unsupported call', f'{name}()')
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            try:
                node.value.encode('ascii')
            except UnicodeEncodeError:
                self.reject(node, 'non-ascii string literal')
        elif isinstance(node.value, complex):
            self.reject(node, 'complex numbers')
        self.generic_visit(node)


def is_range_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ITERABLE_ONLY_BUILTINS
    )


def collect_function_names(tree):
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def parse_and_validate(source):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            tree = ast.parse(source)
    except SyntaxError as error:
        raise UnsupportedFeature('invalid python', error.lineno, error.msg)
    except (ValueError, RecursionError) as error:
        # null bytes, or source nested too deeply to walk
        raise UnsupportedFeature('unparseable python', None, str(error))
    validator = CapabilityValidator()
    # names are gathered first so a call to a function defined further down the
    # file is not mistaken for an unsupported builtin
    validator.function_names = collect_function_names(tree)
    validator.visit(tree)
    return tree
