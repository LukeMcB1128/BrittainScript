"""Turn a validated, lowered Python AST into BrittainScript source.

Statements are emitted one per line because the interpreter parses line by
line, and binary operations are fully parenthesised so the result does not
depend on the two languages agreeing about precedence.
"""

import ast

from .errors import UnsupportedFeature
from .frontend import (
    BINARY_OPERATORS,
    CALLABLE_BUILTINS,
    COMPARISON_OPERATORS,
    ITERABLE_ONLY_BUILTINS,
    is_range_call,
)

INDENT = '    '


def bs_string(value):
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    escaped = escaped.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
    return f'"{escaped}"'


class Emitter(ast.NodeVisitor):
    def __init__(self):
        self.lines = []
        self.depth = 0

    def emit(self, text):
        self.lines.append(INDENT * self.depth + text)

    def unsupported(self, node, feature):
        raise UnsupportedFeature(feature, getattr(node, 'lineno', None))

    # --- module and statements -------------------------------------------
    def emit_module(self, tree):
        self.emit_body(tree.body)
        return '\n'.join(self.lines) + '\n'

    def emit_body(self, statements):
        for statement in statements:
            self.visit(statement)

    def emit_block(self, statements):
        self.depth += 1
        if statements:
            self.emit_body(statements)
        self.depth -= 1
        self.emit('end')

    def visit_FunctionDef(self, node):
        parameters = ', '.join(argument.arg for argument in node.args.args)
        self.emit(f'func {node.name}({parameters}):')
        self.emit_block(node.body)

    def visit_Return(self, node):
        if node.value is None:
            self.emit('return')
        else:
            self.emit(f'return {self.expression(node.value)}')

    def visit_Assign(self, node):
        target = self.expression(node.targets[0])
        self.emit(f'{target} = {self.expression(node.value)}')

    def visit_If(self, node):
        self.emit(f'cond {self.expression(node.test)}:')
        self.depth += 1
        self.emit_body(node.body)
        self.depth -= 1
        self.emit_orelse(node.orelse)
        self.emit('end')

    def emit_orelse(self, orelse):
        if not orelse:
            return
        # 'elif' arrives as a single nested If in the else branch
        if len(orelse) == 1 and isinstance(orelse[0], ast.If):
            nested = orelse[0]
            self.emit(f'elif {self.expression(nested.test)}:')
            self.depth += 1
            self.emit_body(nested.body)
            self.depth -= 1
            self.emit_orelse(nested.orelse)
            return
        self.emit('else:')
        self.depth += 1
        self.emit_body(orelse)
        self.depth -= 1

    def visit_While(self, node):
        self.emit(f'while {self.expression(node.test)}:')
        self.emit_block(node.body)

    def visit_For(self, node):
        iterable = node.iter
        if is_range_call(iterable):
            arguments = ', '.join(self.expression(argument) for argument in iterable.args)
            rendered = f'{ITERABLE_ONLY_BUILTINS["range"]}({arguments})'
        else:
            rendered = self.expression(iterable)
        self.emit(f'for {node.target.id} in {rendered}:')
        self.emit_block(node.body)

    def visit_Break(self, node):
        self.emit('break')

    def visit_Continue(self, node):
        self.emit('continue')

    def visit_Pass(self, node):
        # BrittainScript has no 'pass'; an empty block is written as-is
        pass

    def visit_Expr(self, node):
        rendered = self.expression(node.value)
        self.emit(rendered)

    def generic_visit(self, node):
        self.unsupported(node, type(node).__name__)

    # --- expressions ------------------------------------------------------
    def expression(self, node):
        method = getattr(self, 'expression_' + type(node).__name__, None)
        if method is None:
            self.unsupported(node, type(node).__name__)
        return method(node)

    def expression_Constant(self, node):
        value = node.value
        if value is None:
            return 'null'
        if value is True:
            return 'true'
        if value is False:
            return 'false'
        if isinstance(value, str):
            return bs_string(value)
        if isinstance(value, (int, float)):
            if value < 0:
                # negative literals only reach here inside already-lowered code
                return f'(0 - {abs(value)!r})'
            return repr(value)
        self.unsupported(node, f'constant {type(value).__name__}')

    def expression_Name(self, node):
        return node.id

    def expression_List(self, node):
        return '[' + ', '.join(self.expression(item) for item in node.elts) + ']'

    def expression_BinOp(self, node):
        operator = BINARY_OPERATORS.get(type(node.op))
        if operator is None:
            self.unsupported(node, type(node.op).__name__)
        return f'({self.expression(node.left)} {operator} {self.expression(node.right)})'

    def expression_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            return f'(not {self.expression(node.operand)})'
        self.unsupported(node, type(node.op).__name__)

    def expression_BoolOp(self, node):
        operator = 'and' if isinstance(node.op, ast.And) else 'or'
        rendered = f' {operator} '.join(self.expression(value) for value in node.values)
        return f'({rendered})'

    def expression_Compare(self, node):
        operator = COMPARISON_OPERATORS.get(type(node.ops[0]))
        if operator is None:
            self.unsupported(node, type(node.ops[0]).__name__)
        left = self.expression(node.left)
        right = self.expression(node.comparators[0])
        return f'({left} {operator} {right})'

    def expression_Subscript(self, node):
        value = self.expression(node.value)
        if isinstance(node.slice, ast.Slice):
            lower = self.expression(node.slice.lower) if node.slice.lower else ''
            upper = self.expression(node.slice.upper) if node.slice.upper else ''
            return f'{value}[{lower}:{upper}]'
        return f'{value}[{self.expression(node.slice)}]'

    def expression_JoinedStr(self, node):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(bs_string(str(value.value)))
            else:
                parts.append(f'tostr({self.expression(value.value)})')
        if not parts:
            return '""'
        return '(' + ' + '.join(parts) + ')'

    def expression_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            receiver = self.expression(node.func.value)
            arguments = ', '.join(self.expression(argument) for argument in node.args)
            return f'{receiver}.{node.func.attr}({arguments})'
        name = node.func.id
        if name == 'print':
            return self.emit_print(node)
        translated = CALLABLE_BUILTINS.get(name, name)
        arguments = ', '.join(self.expression(argument) for argument in node.args)
        return f'{translated}({arguments})'

    def emit_print(self, node):
        if not node.args:
            return 'push("")'
        if len(node.args) == 1:
            return f'push({self.expression(node.args[0])})'
        # print(a, b) joins with a space after str()-ing each argument
        parts = []
        for index, argument in enumerate(node.args):
            if index:
                parts.append('" "')
            parts.append(f'tostr({self.expression(argument)})')
        return 'push(' + ' + '.join(parts) + ')'


def emit(tree):
    return Emitter().emit_module(tree)
