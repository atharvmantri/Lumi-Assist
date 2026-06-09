"""Calculator — precise computation via Python."""
from __future__ import annotations

import ast
import math
import operator

from tools import tool


# Safe math expression evaluator — no eval/exec
_ALLOWED_NAMES = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "pow": pow, "sqrt": math.sqrt,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "pi": math.pi, "e": math.e, "tau": math.tau,
    "ceil": math.ceil, "floor": math.floor,
    "factorial": math.factorial,
    "inf": math.inf,
}

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


def _safe_eval(node: ast.AST) -> float | int:
    """Evaluate a math expression safely (no file IO, no import, no exec)."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"unsupported operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"unsupported unary operator: {op_type.__name__}")
        val = _safe_eval(node.operand)
        return _OPERATORS[op_type](val)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("only simple function calls allowed")
        func_name = node.func.id
        if func_name not in _ALLOWED_NAMES:
            raise ValueError(f"unknown function: {func_name}")
        args = [_safe_eval(a) for a in node.args]
        return _ALLOWED_NAMES[func_name](*args)
    elif isinstance(node, ast.Name):
        if node.id in _ALLOWED_NAMES and isinstance(_ALLOWED_NAMES[node.id], (int, float)):
            return _ALLOWED_NAMES[node.id]
        raise ValueError(f"unknown name: {node.id}")
    else:
        raise ValueError(f"unsupported expression: {type(node).__name__}")


@tool(
    name="calculate",
    description=(
        "Evaluate a mathematical expression precisely. Use when the user asks "
        "for a calculation, math problem, or numeric computation. "
        "Supports: +, -, *, /, //, %, ^, sqrt, sin, cos, tan, log, factorial, pi, e. "
        "Examples: '2 + 2', 'sqrt(144)', 'sin(pi/4)', 'factorial(10)', 'log(1000)'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression to evaluate (e.g. 'sqrt(144) * 3 + 2')",
            },
        },
        "required": ["expression"],
    },
)
def calculate(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        # Format nicely
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                result = int(result)
            else:
                result = round(result, 10)
        return f"{expression} = {result}"
    except Exception as e:
        return f"error evaluating '{expression}': {e}"


@tool(
    name="convert_units",
    description="Convert between common units: temperature, length, weight, volume.",
    parameters={
        "type": "object",
        "properties": {
            "value": {
                "type": "number",
                "description": "Numeric value to convert",
            },
            "from_unit": {
                "type": "string",
                "description": "Source unit: 'celsius', 'fahrenheit', 'meters', 'feet', 'inches', 'cm', 'km', 'miles', 'kg', 'lbs', 'grams', 'oz', 'liters', 'gallons'",
            },
            "to_unit": {
                "type": "string",
                "description": "Target unit (same options as from_unit)",
            },
        },
        "required": ["value", "from_unit", "to_unit"],
    },
)
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    # Temperature
    temp_units = {"celsius", "fahrenheit", "kelvin"}
    if from_unit in temp_units and to_unit in temp_units:
        if from_unit == to_unit:
            return f"{value} {from_unit} = {value} {to_unit}"
        # Convert to Celsius first
        if from_unit == "celsius":
            c = value
        elif from_unit == "fahrenheit":
            c = (value - 32) * 5 / 9
        elif from_unit == "kelvin":
            c = value - 273.15

        # Convert from Celsius to target
        if to_unit == "celsius":
            result = c
        elif to_unit == "fahrenheit":
            result = c * 9 / 5 + 32
        elif to_unit == "kelvin":
            result = c + 273.15

        return f"{value} {from_unit} = {result:.2f} {to_unit}"

    # Length (convert to meters first)
    length_to_m = {
        "meters": 1, "meter": 1, "m": 1,
        "km": 1000, "kilometers": 1000,
        "cm": 0.01, "centimeters": 0.01,
        "mm": 0.001, "millimeters": 0.001,
        "feet": 0.3048, "foot": 0.3048, "ft": 0.3048,
        "inches": 0.0254, "inch": 0.0254, "in": 0.0254,
        "miles": 1609.344, "mile": 1609.344, "mi": 1609.344,
        "yards": 0.9144, "yard": 0.9144, "yd": 0.9144,
    }
    if from_unit in length_to_m and to_unit in length_to_m:
        meters = value * length_to_m[from_unit]
        result = meters / length_to_m[to_unit]
        return f"{value} {from_unit} = {result:.4f} {to_unit}"

    # Weight (convert to kg first)
    weight_to_kg = {
        "kg": 1, "kilograms": 1, "kilogram": 1,
        "grams": 0.001, "gram": 0.001, "g": 0.001,
        "lbs": 0.453592, "pounds": 0.453592, "pound": 0.453592, "lb": 0.453592,
        "oz": 0.0283495, "ounces": 0.0283495, "ounce": 0.0283495,
    }
    if from_unit in weight_to_kg and to_unit in weight_to_kg:
        kg = value * weight_to_kg[from_unit]
        result = kg / weight_to_kg[to_unit]
        return f"{value} {from_unit} = {result:.4f} {to_unit}"

    # Volume (convert to liters first)
    volume_to_l = {
        "liters": 1, "liter": 1, "l": 1,
        "ml": 0.001, "milliliters": 0.001,
        "gallons": 3.78541, "gallon": 3.78541, "gal": 3.78541,
        "quarts": 0.946353, "quart": 0.946353,
        "cups": 0.236588, "cup": 0.236588,
        "floz": 0.0295735, "fluid_ounces": 0.0295735,
    }
    if from_unit in volume_to_l and to_unit in volume_to_l:
        liters = value * volume_to_l[from_unit]
        result = liters / volume_to_l[to_unit]
        return f"{value} {from_unit} = {result:.4f} {to_unit}"

    return f"error: unknown units '{from_unit}' or '{to_unit}'. Supported: temperature (celsius/fahrenheit/kelvin), length (m/km/cm/mm/feet/inches/miles/yards), weight (kg/g/lbs/oz), volume (liters/ml/gallons/quarts/cups)"
