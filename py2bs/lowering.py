"""Tree rewrites applied before emitting.

Two of these exist because BrittainScript lacks a construct (unary minus,
augmented assignment). The third exists because BrittainScript's scoping
differs from Python's in a way that silently produces wrong answers.
"""

import ast


class AugmentedAssignmentLowering(ast.NodeTransformer):
    """x += 1  ->  x = x + 1"""

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        target = node.target
        value_target = ast.copy_location(clone_as_load(target), target)
        binary = ast.copy_location(ast.BinOp(left=value_target, op=node.op, right=node.value), node)
        return ast.copy_location(ast.Assign(targets=[target], value=binary), node)


class UnaryMinusLowering(ast.NodeTransformer):
    """-x  ->  (0 - x); BrittainScript has no unary minus"""

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.USub):
            zero = ast.copy_location(ast.Constant(value=0), node)
            return ast.copy_location(
                ast.BinOp(left=zero, op=ast.Sub(), right=node.operand), node
            )
        if isinstance(node.op, ast.UAdd):
            return node.operand
        return node


class FloorDivisionLowering(ast.NodeTransformer):
    """a // b  ->  floor(a / b)

    Exact for integers, which is what '//' is nearly always used for. On floats
    Python keeps a float where floor() returns an int, so those show up as a
    stdout mismatch during verification rather than passing quietly.
    """

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if not isinstance(node.op, ast.FloorDiv):
            return node
        division = ast.copy_location(
            ast.BinOp(left=node.left, op=ast.Div(), right=node.right), node
        )
        call = ast.Call(
            func=ast.copy_location(ast.Name(id='floor', ctx=ast.Load()), node),
            args=[division],
            keywords=[],
        )
        return ast.copy_location(call, node)


class LocalRenaming(ast.NodeTransformer):
    """Give every function-local name a unique name.

    In Python a name assigned anywhere in a function is local to it. In
    BrittainScript, set_name walks outward and assigns to a matching outer name
    instead, so a function that assigns to a name also used at module level
    silently mutates the global. Renaming locals removes the collision.
    """

    def __init__(self, module_names):
        self.module_names = module_names
        self.used_names = set(module_names)

    def visit_FunctionDef(self, node):
        locals_in_function = collect_local_names(node)
        renaming = {}
        for name in sorted(locals_in_function):
            if name in self.module_names:
                renaming[name] = self.fresh_name(node.name, name)
        if renaming:
            Renamer(renaming).visit(node)
        self.generic_visit(node)
        return node

    def fresh_name(self, function_name, name):
        candidate = f'{function_name}_{name}'
        while candidate in self.used_names:
            candidate = f'_{candidate}'
        self.used_names.add(candidate)
        return candidate


class Renamer(ast.NodeTransformer):
    def __init__(self, renaming):
        self.renaming = renaming

    def visit_Name(self, node):
        if node.id in self.renaming:
            node.id = self.renaming[node.id]
        return node

    def visit_arg(self, node):
        if node.arg in self.renaming:
            node.arg = self.renaming[node.arg]
        return node


def clone_as_load(node):
    if isinstance(node, ast.Name):
        return ast.Name(id=node.id, ctx=ast.Load())
    if isinstance(node, ast.Subscript):
        return ast.Subscript(value=node.value, slice=node.slice, ctx=ast.Load())
    return node


def collect_local_names(function_node):
    names = {argument.arg for argument in function_node.args.args}
    for node in ast.walk(function_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
    return names


def collect_module_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def lower(tree):
    tree = AugmentedAssignmentLowering().visit(tree)
    tree = UnaryMinusLowering().visit(tree)
    tree = FloorDivisionLowering().visit(tree)
    LocalRenaming(collect_module_names(tree)).visit(tree)
    ast.fix_missing_locations(tree)
    return tree
