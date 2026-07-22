from __future__ import annotations

import asyncio
import logging

from aios.cli.main import _build_registry, get_provider_and_model
from aios.desktop.server import DesktopIPCServer
from aios.runtime.runtime import Runtime, RuntimeConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aios.desktop")

async def main():
    logger.info("Initializing Desktop IPC Server using Runtime...")
    
    provider_obj, settings, provider_name, model_name = get_provider_and_model(None, None)
    tool_registry = _build_registry(settings)
    
    from aios.desktop.hands import register_hands_tools
    from aios.desktop.vision.module import BasicVision
    from aios.desktop.vision.tool import ViewScreenTool

    register_hands_tools(tool_registry)
    
    vision = BasicVision(enable_ocr=True)
    tool_registry.register(ViewScreenTool(vision))
    
    desktop_prompt = (
        "\\n\\n[Desktop Environment]\\n"
        "You are operating in a Desktop GUI environment. You have tools like `view_screen`, `move_mouse`, `click`, and `type_text`.\\n"
        "To accomplish a desktop task:\\n"
        "1. Always start by using `view_screen` to capture and analyze the screen layout.\\n"
        "2. Identify the exact (x, y) coordinates of the element you need to interact with from the view_screen output.\\n"
        "3. Use `move_mouse` or `click` to interact with that element.\\n"
        "4. If you need to type, click on the text field first, then use `type_text`.\\n"
        "5. Loop this process (view_screen -> action -> view_screen -> action) until the user's task is completed."
    )
    config = RuntimeConfig(
        provider=provider_obj,
        tool_registry=tool_registry,
        mcp_enabled=bool(settings.mcp_servers),
        system_prompt=desktop_prompt,
    )
    
    async with Runtime(config) as runtime:
        server = DesktopIPCServer(runtime=runtime, host="127.0.0.1", port=8765)
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
