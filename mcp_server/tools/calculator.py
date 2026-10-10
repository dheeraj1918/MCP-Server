import ast, operator, math

_ALLOWED = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def _eval(node):
    if isinstance(node, ast.Expression): return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
        if isinstance(node.op, ast.Pow) and abs(node.right.value if isinstance(node.right, ast.Constant) else 999) > 100:
            raise ValueError("Exponent too large")
        return _ALLOWED[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED: return _ALLOWED[type(node.op)](_eval(node.operand))
    raise ValueError("Only basic arithmetic is supported.")

def register(mcp):
    @mcp.tool()
    def calculator(expression: str) -> str:
        """Evaluate a basic arithmetic expression, e.g. '(12 + 4) / 2'."""
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree)
        if not math.isfinite(float(result)): raise ValueError("Result is not finite")
        return str(result)
