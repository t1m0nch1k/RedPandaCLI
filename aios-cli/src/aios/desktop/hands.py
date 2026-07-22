from __future__ import annotations

from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool

try:
    import pyautogui

    pyautogui.FAILSAFE = True
    _PYAUTOGUI_ERROR: str | None = None
except Exception as _exc:
    pyautogui = None
    _PYAUTOGUI_ERROR = str(_exc)


def _unavailable() -> ToolResult:
    return ToolResult(
        success=False,
        error=f"pyautogui is unavailable (install extra [desktop]): {_PYAUTOGUI_ERROR}",
    )


class MoveMouseTool(Tool):
    name = "move_mouse"
    description = "Move mouse cursor to (x, y) or relative to current position"
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "number"},
            "y": {"type": "number"},
            "duration": {"type": "number", "default": 0.2},
            "relative": {"type": "boolean", "default": False, "description": "If true, move relative to current position"},
        },
        "required": ["x", "y"],
    }

    async def run(self, **params: Any) -> ToolResult:
        if pyautogui is None:
            return _unavailable()
        try:
            dx, dy = int(float(params["x"])), int(float(params["y"]))
        except (KeyError, ValueError):
            return ToolResult(success=False, error="Need numeric x and y")
        duration = float(params.get("duration", 0.2))
        if params.get("relative"):
            cx, cy = pyautogui.position()
            pyautogui.moveTo(cx + dx, cy + dy, duration=duration)
            return ToolResult(success=True, output=f"Cursor moved by ({dx}, {dy})")
        pyautogui.moveTo(dx, dy, duration=duration)
        return ToolResult(success=True, output=f"Mouse moved to ({dx}, {dy})")


class ClickTool(Tool):
    name = "click"
    description = "Click mouse (at current position or at specific coordinates)"
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "number"},
            "y": {"type": "number"},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
            "clicks": {"type": "integer", "default": 1},
        },
    }

    async def run(self, **params: Any) -> ToolResult:
        if pyautogui is None:
            return _unavailable()
        kwargs: dict[str, Any] = {
            "button": params.get("button", "left"),
            "clicks": int(params.get("clicks", 1)),
        }
        if "x" in params and "y" in params:
            kwargs["x"] = int(float(params["x"]))
            kwargs["y"] = int(float(params["y"]))
        pyautogui.click(**kwargs)
        return ToolResult(success=True, output="Click executed")


class TypeTextTool(Tool):
    name = "type_text"
    description = "Type text into active window"
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "interval": {"type": "number", "default": 0.02},
        },
        "required": ["text"],
    }

    async def run(self, **params: Any) -> ToolResult:
        if pyautogui is None:
            return _unavailable()
        text = str(params.get("text", ""))
        if not text:
            return ToolResult(success=False, error="Empty text")
        pyautogui.write(text, interval=float(params.get("interval", 0.02)))
        return ToolResult(success=True, output=f"Typed {len(text)} characters")


class GetCursorPosTool(Tool):
    name = "get_cursor_pos"
    description = "Get current mouse cursor coordinates"
    parameters = {"type": "object", "properties": {}}

    async def run(self, **params: Any) -> ToolResult:
        if pyautogui is None:
            return _unavailable()
        x, y = pyautogui.position()
        return ToolResult(
            success=True,
            output=f"Cursor at: ({x}, {y})",
            data={"x": x, "y": y},
        )


class DragTool(Tool):
    name = "drag"
    description = "Drag mouse from one point to another"
    parameters = {
        "type": "object",
        "properties": {
            "from_x": {"type": "number"},
            "from_y": {"type": "number"},
            "to_x": {"type": "number"},
            "to_y": {"type": "number"},
            "button": {"type": "string", "enum": ["left", "right"], "default": "left"},
            "duration": {"type": "number", "default": 0.5},
        },
        "required": ["from_x", "from_y", "to_x", "to_y"],
    }

    async def run(self, **params: Any) -> ToolResult:
        if pyautogui is None:
            return _unavailable()
        try:
            fx = int(float(params["from_x"]))
            fy = int(float(params["from_y"]))
            tx = int(float(params["to_x"]))
            ty = int(float(params["to_y"]))
        except (KeyError, ValueError):
            return ToolResult(success=False, error="Need numeric from_x, from_y, to_x, to_y")
        button = params.get("button", "left")
        duration = float(params.get("duration", 0.5))
        pyautogui.moveTo(fx, fy, duration=duration * 0.3)
        pyautogui.dragTo(tx, ty, button=button, duration=duration)
        return ToolResult(
            success=True,
            output=f"Dragged from ({fx},{fy}) to ({tx},{ty})",
            data={"from": {"x": fx, "y": fy}, "to": {"x": tx, "y": ty}},
        )


class ScrollTool(Tool):
    name = "scroll"
    description = "Scroll with mouse wheel"
    parameters = {
        "type": "object",
        "properties": {
            "clicks": {"type": "integer", "default": -3, "description": "Positive = up, negative = down"},
            "x": {"type": "number", "description": "Optional: move mouse to x before scroll"},
            "y": {"type": "number", "description": "Optional: move mouse to y before scroll"},
        },
    }

    async def run(self, **params: Any) -> ToolResult:
        if pyautogui is None:
            return _unavailable()
        clicks = int(params.get("clicks", -3))
        if "x" in params and "y" in params:
            pyautogui.moveTo(int(float(params["x"])), int(float(params["y"])), duration=0.1)
        pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return ToolResult(success=True, output=f"Scrolled {direction} by {abs(clicks)}")


def register_hands_tools(registry: Any) -> None:
    registry.register(MoveMouseTool())
    registry.register(ClickTool())
    registry.register(TypeTextTool())
    registry.register(GetCursorPosTool())
    registry.register(DragTool())
    registry.register(ScrollTool())
