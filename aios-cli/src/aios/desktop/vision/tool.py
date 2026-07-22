from typing import Any

from aios.core.models import ToolResult
from aios.desktop.vision.capture import capture_screen_png
from aios.desktop.vision.module import BasicVision
from aios.tools.base import Tool


class ViewScreenTool(Tool):
    name = "view_screen"
    description = "Take a screenshot and analyze it to find windows, buttons, and text coordinates on the screen. Use this before interacting with the UI to find exact coordinates for clicking or typing."
    parameters = {"type": "object", "properties": {}}

    def __init__(self, vision_engine: BasicVision) -> None:
        self.vision = vision_engine

    async def run(self, **kwargs: Any) -> ToolResult:
        try:
            png_bytes = await capture_screen_png()
            analysis = await self.vision.analyze(png_bytes)
            
            # Format the output for the LLM
            data = analysis.model_dump()
            
            summary_parts = []
            windows = data.get("windows", [])
            texts = data.get("text", [])
            
            if windows:
                summary_parts.append(f"Windows ({len(windows)}):")
                for w in windows[:10]:
                    title = w.get("title", "?")
                    x, y = w.get("left", w.get("x", 0)), w.get("top", w.get("y", 0))
                    w_, h = w.get("width", 0), w.get("height", 0)
                    summary_parts.append(f"  - {title} at ({x},{y}) size {w_}x{h}")
                    
            if texts:
                summary_parts.append(f"\\nDetected text ({len(texts)}):")
                for t in texts[:50]:
                    txt = t.get('text', '')
                    if txt:
                        x, y = t.get("left", 0), t.get("top", 0)
                        summary_parts.append(f"  - '{txt}' at ({x},{y})")
            
            summary = "\\n".join(summary_parts) if summary_parts else "No UI elements detected on screen."
            
            import base64
            image_b64 = base64.b64encode(png_bytes).decode("ascii")
            
            return ToolResult(
                success=True,
                output=f"Screen analyzed successfully. Use these coordinates for move_mouse and click.\\n\\n{summary}",
                data=data,
                image_b64=image_b64
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Failed to view screen: {exc}")
