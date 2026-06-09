"""Mouse control — move, click, drag, scroll."""
from __future__ import annotations

from tools import tool


@tool(
    name="mouse_click",
    description="Click the mouse at the current position or at specific coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "x": {
                "type": "integer",
                "description": "X coordinate (optional, uses current position if omitted)",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate (optional, uses current position if omitted)",
            },
            "button": {
                "type": "string",
                "description": "Mouse button: 'left', 'right', 'middle' (default 'left')",
                "enum": ["left", "right", "middle"],
            },
            "clicks": {
                "type": "integer",
                "description": "Number of clicks (1 for single, 2 for double)",
            },
        },
        "required": [],
    },
)
def mouse_click(x: int = 0, y: int = 0, button: str = "left", clicks: int = 1) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        if x > 0 and y > 0:
            pyautogui.click(x, y, clicks=clicks, button=button)
            return f"clicked at ({x}, {y})"
        else:
            pyautogui.click(clicks=clicks, button=button)
            return f"clicked at current position"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="mouse_move",
    description="Move the mouse cursor to specific coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "x": {
                "type": "integer",
                "description": "X coordinate on screen",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate on screen",
            },
        },
        "required": ["x", "y"],
    },
)
def mouse_move(x: int, y: int) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.moveTo(x, y)
        return f"mouse moved to ({x}, {y})"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_mouse_position",
    description="Get the current mouse cursor position.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_mouse_position() -> str:
    try:
        import pyautogui
        pos = pyautogui.position()
        return f"Mouse at: ({pos.x}, {pos.y})"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="scroll",
    description="Scroll the mouse wheel up or down.",
    parameters={
        "type": "object",
        "properties": {
            "amount": {
                "type": "integer",
                "description": "Scroll amount (positive = up, negative = down)",
            },
        },
        "required": ["amount"],
    },
)
def scroll(amount: int) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.scroll(amount)
        direction = "up" if amount > 0 else "down"
        return f"scrolled {direction} by {abs(amount)}"
    except Exception as e:
        return f"error: {e}"
