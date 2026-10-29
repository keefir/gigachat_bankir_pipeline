import ast
import operator

from langchain_core.tools import tool

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval(node.operand))
    raise ValueError("Недопустимое выражение")


@tool
def calculator(expression: str) -> dict:
    """Калькулятор. Схема для модели — schemas/calculator.json."""
    try:
        return {"result": str(_eval(ast.parse(expression, mode="eval").body))}
    except Exception as exc:
        return {"error": f"Ошибка вычисления: {exc}"}
