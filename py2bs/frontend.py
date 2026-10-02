"""Parse Python and reject anything outside the translatable subset.

Everything here runs before a single line is emitted, so a rejection names the
feature and the line rather than producing BrittainScript that quietly means
something else.
"""

import ast
import builtins
import importlib.machinery
import warnings

from .errors import UnsupportedFeature

# builtins with an exact BrittainScript equivalent
CALLABLE_BUILTINS = {
    'print': 'push',
    'len': 'len',
    'str': 'tostr',
    'abs': 'absolute',
    'round': 'round',
    'dict': 'dict',
    'list': 'list',
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
    'get', 'keys', 'values', 'items', 'copy', 'update', 'setdefault',
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
    ast.FloorDiv: '//',
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

# words the lexer turns into their own token: unusable as any name at all
LEXER_KEYWORDS = {
    'sqrroot', 'sin', 'cos', 'tan', 'pi', 'push', 'and', 'or', 'not', 'true',
    'false', 'null', 'cond', 'space',
}

# words matched at the start of a statement. A function may be called 'add',
# because a call never starts a line with 'add ', but a variable may not be:
# 'add = 5' is read as a library import.
STATEMENT_KEYWORDS = {
    'while', 'for', 'func', 'end', 'return', 'break', 'continue', 'add',
    'elif', 'else', 'in', 'local', 'discard',
    'try', 'catch', 'finally', 'raise',
}

BS_KEYWORDS = LEXER_KEYWORDS | STATEMENT_KEYWORDS

EXCEPTION_TYPES = {
    name for name, value in vars(builtins).items()
    if isinstance(value, type) and issubclass(value, Exception)
    and name not in ('ExceptionGroup',)
}

# pyimport resolves a real module, so a translated program can reach anything
# installed. Verification runs the Python, so modules that touch the world
# outside the process are refused rather than executed.
UNSAFE_IMPORTS = {
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'urllib', 'http', 'requests',
    'ftplib', 'smtplib', 'tempfile', 'glob', 'pathlib', 'sqlite3', 'pickle',
    'shelve', 'ctypes', 'multiprocessing', 'threading', 'signal', 'webbrowser',
    'asyncio', 'importlib', 'builtins', 'atexit', 'gc', 'mmap', 'fcntl',
    'platform', 'getpass', 'io', 'fileinput', 'zipfile', 'tarfile',
}


def module_is_available(name):
    # Resolve each package path without importing a parent package. find_spec()
    # from importlib.util imports parents when the name contains a dot.
    try:
        path = None
        parts = name.split('.')
        for index in range(len(parts)):
            fullname = '.'.join(parts[:index + 1])
            spec = None
            if index == 0:
                spec = importlib.machinery.BuiltinImporter.find_spec(fullname)
                if spec is None:
                    spec = importlib.machinery.FrozenImporter.find_spec(fullname)
            if spec is None:
                # The parent path is explicit. Use the leaf name so namespace
                # package specs do not look for an unimported parent in sys.modules.
                spec = importlib.machinery.PathFinder.find_spec(parts[index], path)
            if spec is None:
                return False
            locations = spec.submodule_search_locations
            path = list(locations) if locations is not None else None
            if index < len(parts) - 1 and path is None:
                return False
        return True
    except (ImportError, ValueError, ModuleNotFoundError, OSError):
        return False


def attribute_root(node):
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


COMPARISON_OPERATORS = {
    ast.Eq: '==',
    ast.NotEq: '!=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.Gt: '>',
    ast.GtE: '>=',
    ast.In: 'in',
    ast.NotIn: 'not in',
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
    def __init__(self, survey=None):
        self.function_names = set()
        self.imported_names = set()
        self.exception_names = set()
        self.function_depth = 0
        # When survey is a set, rejections are COLLECTED instead of raised, so one
        # pass reports every unsupported construct in a file rather than the first
        # one encountered. Translation never uses this — see survey_features().
        self.survey = survey
        self._descended = set()

    def reject(self, node, feature, detail=None):
        if self.survey is None:
            raise UnsupportedFeature(feature, getattr(node, 'lineno', None), detail)
        # Feature granularity should match IMPLEMENTATION granularity, and these
        # two are not one task each — they are a list of missing builtins, where
        # adding sorted() has nothing to do with adding zip(). Recorded coarsely
        # they are the largest addressable bar on the board and tell you nothing
        # about what to write. Recorded with the name, the survey ranks the
        # builtins directly.
        if detail and feature in ('unsupported call', 'unsupported method'):
            self.survey.add(f'{feature} {detail}')
        else:
            self.survey.add(feature)
        # Normal rejection aborts the walk, so most visit_* methods return without
        # descending. Keep descending here or everything nested inside a class body
        # stays invisible, which is exactly the measurement being taken.
        self.generic_visit(node)

    def generic_visit(self, node):
        """Walk each node's children at most once per survey.

        In survey mode a node is reached repeatedly: reject() descends so a
        rejected subtree still gets measured, the visit_* method that called
        reject descends again when it returns, and several methods reject twice.
        Re-walking every time costs N^depth. Fourteen nested functions with
        default arguments took 17 seconds, and one real file from The Stack
        pinned a survey run at 100% CPU with no progress for minutes.

        Translation is unaffected — reject() raises there and never reaches this.
        """
        if self.survey is not None:
            # Keyed on function_depth, not the node alone: reject() descends
            # before visit_FunctionDef has counted the function it is inside, so
            # the same subtree legitimately yields different results at different
            # depths. Keying on id(node) alone silently lost 'nested functions'
            # in 30 of 5,136 files.
            key = (id(node), self.function_depth)
            if key in self._descended:
                return
            self._descended.add(key)
        super().generic_visit(node)

    # --- wholly unsupported statements -----------------------------------
    def visit_ClassDef(self, node):
        self.reject(node, 'classes')

    def visit_Import(self, node):
        for alias in node.names:
            if '.' in alias.name and not alias.asname:
                self.reject(node, 'dotted import', alias.name)
            self.check_module(node, alias.name)
            self.check_binding(node, alias.asname or alias.name)

    def visit_ImportFrom(self, node):
        if node.level:
            self.reject(node, 'relative imports')
        if any(alias.name == '*' for alias in node.names):
            self.reject(node, 'star imports')
        self.check_module(node, node.module)
        for alias in node.names:
            self.check_binding(node, alias.asname or alias.name)

    def check_module(self, node, name):
        if not name:
            self.reject(node, 'imports')
        root = name.split('.')[0]
        if root in UNSAFE_IMPORTS:
            self.reject(node, 'unsafe import', f'{root} can affect the world outside the program')
        if not module_is_available(name):
            self.reject(node, 'unresolvable import', f"no module named '{name}'")

    def check_binding(self, node, name):
        if name in BS_KEYWORDS:
            self.reject(node, 'name collides with a keyword', name)
        if name in EXCEPTION_TYPES:
            self.reject(node, 'exception type binding', name)
        self.imported_names.add(name)

    def visit_Try(self, node):
        for statement in node.body:
            self.visit(statement)
        catch_all = False
        for handler in node.handlers:
            if catch_all:
                self.reject(handler, 'exception handler order', 'the catch-all handler must be last')
            if handler.type is not None and (
                not isinstance(handler.type, ast.Name) or handler.type.id not in EXCEPTION_TYPES
            ):
                self.reject(handler, 'exception handler type', 'use one built-in exception type')
            catch_all = handler.type is None or (
                isinstance(handler.type, ast.Name) and handler.type.id == 'Exception'
            )
            if handler.name:
                if handler.name in BS_KEYWORDS:
                    self.reject(handler, 'name collides with a keyword', handler.name)
                if handler.name in EXCEPTION_TYPES:
                    self.reject(handler, 'exception type binding', handler.name)
                self.exception_names.add(handler.name)
            for statement in handler.body:
                self.visit(statement)
        for statement in node.orelse + node.finalbody:
            self.visit(statement)

    def visit_TryStar(self, node):
        self.reject(node, 'exception groups')

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
        if node.cause is not None:
            self.reject(node, 'exception chaining')
        self.generic_visit(node)

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
        if any(key is None for key in node.keys):
            self.reject(node, 'dictionary unpacking')
        self.generic_visit(node)

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
        if node.name in LEXER_KEYWORDS or node.name in ('try', 'catch', 'finally', 'raise'):
            self.reject(node, 'name collides with a keyword', node.name)
        if node.name in EXCEPTION_TYPES:
            self.reject(node, 'exception type binding', node.name)
        for argument in node.args.args:
            if argument.arg in BS_KEYWORDS:
                self.reject(node, 'name collides with a keyword', argument.arg)
            if argument.arg in EXCEPTION_TYPES:
                self.reject(node, 'exception type binding', argument.arg)
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
        if isinstance(target, ast.Name) and target.id in BS_KEYWORDS:
            self.reject(node, 'name collides with a keyword', target.id)
        if isinstance(target, ast.Name) and target.id in EXCEPTION_TYPES:
            self.reject(node, 'exception type binding', target.id)
        self.generic_visit(node)

    def visit_For(self, node):
        if node.orelse:
            self.reject(node, 'loop else')
        if not isinstance(node.target, ast.Name):
            self.reject(node, 'tuple unpacking')
        # elif, because reject() only raises when translating. A survey collects
        # and walks on, and `.id` does not exist on the Tuple we just rejected.
        elif node.target.id in BS_KEYWORDS:
            self.reject(node, 'name collides with a keyword', node.target.id)
        elif node.target.id in EXCEPTION_TYPES:
            self.reject(node, 'exception type binding', node.target.id)
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
        if isinstance(node.target, ast.Name) and node.target.id in BS_KEYWORDS:
            self.reject(node, 'name collides with a keyword', node.target.id)
        if isinstance(node.target, ast.Name) and node.target.id in EXCEPTION_TYPES:
            self.reject(node, 'exception type binding', node.target.id)
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
        # reading a member of an imported module is fine; any other bare
        # attribute means an object model BrittainScript does not have
        if (attribute_root(node) not in self.imported_names
                and not (attribute_root(node) in self.exception_names and node.attr == 'args')):
            self.reject(node, 'attribute access')
        self.generic_visit(node)

    def visit_Call(self, node):
        if node.keywords:
            self.reject(node, 'keyword arguments')
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
            if attribute_root(node.func) in self.imported_names:
                self.visit(node.func.value)
                for argument in node.args:
                    self.visit(argument)
                return
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
            return          # unreachable when translating; reject() raised
        name = node.func.id
        if name in ITERABLE_ONLY_BUILTINS:
            self.reject(node, f'{name}() outside a for loop')
        if name in ('open', 'input', 'eval', 'exec', '__import__'):
            self.reject(node, 'I/O or dynamic execution', f'{name}()')
        if (
            name not in CALLABLE_BUILTINS
            and name not in EXCEPTION_TYPES
            and name not in self.function_names
            and name not in self.imported_names
        ):
            self.reject(node, 'unsupported call', f'{name}()')
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, complex):
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


def collect_imported_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


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
    validator.imported_names = collect_imported_names(tree)
    validator.visit(tree)
    return tree


def survey_features(source):
    """Every construct in `source` that py2bs cannot translate, as a set.

    parse_and_validate raises on the FIRST unsupported construct, which is right
    for translating and useless for planning: a corpus histogram built from it
    counts a file using classes AND dicts AND comprehensions exactly once, under
    whichever the validator happened to check first. The counts then cannot be
    added up, and the cheap features hide behind the expensive ones.

    This walks the whole file and returns all of them, so "which set of features
    unlocks the most files" becomes an answerable question instead of a guess.
    An empty set means the file would pass validation.

    Never executes anything — this is a pure AST walk, unlike verification.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            tree = ast.parse(source)
    except SyntaxError:
        return {'invalid python'}
    except (ValueError, RecursionError):
        return {'unparseable python'}

    found = set()
    validator = CapabilityValidator(survey=found)
    validator.function_names = collect_function_names(tree)
    validator.imported_names = collect_imported_names(tree)
    try:
        validator.visit(tree)
    except RecursionError:
        found.add('unparseable python')
    except Exception:
        # A validator that only ever ran to the first rejection can hit states it
        # was never written for once it keeps walking. Partial results are still
        # usable; a crashed survey of one file must not stop the scan.
        found.add('survey error')
    return found
