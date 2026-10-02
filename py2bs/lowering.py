"""Rewrite unary signs into supported BrittainScript expressions."""

import ast


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
        elif isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def lower(tree):
    tree = UnaryMinusLowering().visit(tree)
    ast.fix_missing_locations(tree)
    return tree
