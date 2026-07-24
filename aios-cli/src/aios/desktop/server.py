from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection, serve

from aios.core.models import Conversation, Role
from aios.desktop.scheduler import ProactiveScheduler
from aios.desktop.vision.module import BasicVision
from aios.runtime.runtime import Runtime

logger = logging.getLogger("aios.desktop.server")

JSONRPC_PARSE_ERROR = -32700
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INTERNAL_ERROR = -32603

class DesktopIPCServer:
    def __init__(
        self,
        runtime: Runtime,
        host: str = "127.0.0.1",
        port: int = 8765,
    ):
        self.runtime = runtime
        self.host = host
        self.port = port
        self._clients: set[ServerConnection] = set()
        self._voice_buffers: dict[ServerConnection, bytearray] = {}
        self.stt_engine = None
        self.vision = BasicVision(enable_ocr=True)
        self.scheduler = ProactiveScheduler(self, self.runtime)
        
        # Register tool hook
        from aios.hooks.events import HookEvent
        if hasattr(self.runtime, "executor") and hasattr(self.runtime.executor, "hook_manager"):
            self.runtime.executor.hook_manager.register(HookEvent.POST_TOOL, self._on_post_tool)

    async def _on_post_tool(self, context: Any) -> Any:
        from aios.hooks.events import HookAction
        if context.tool_name and context.tool_args:
            result_dict = context.tool_result.model_dump() if context.tool_result and hasattr(context.tool_result, "model_dump") else str(context.tool_result)
            await self._broadcast("tool.usage", {
                "name": context.tool_name,
                "args": context.tool_args,
                "result": result_dict,
            })
        return HookAction.CONTINUE

    async def _broadcast(self, method: str, params: dict[str, Any]) -> None:
        if not self._clients:
            return
        msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params}, ensure_ascii=False)
        websockets.broadcast(self._clients, msg)

    async def serve_forever(self) -> None:
        async with serve(self._handle_client, self.host, self.port, max_size=10_485_760) as server:
            self.server = server
            logger.info("Desktop IPC server listening on ws://%s:%d", self.host, self.port)
            self.scheduler.start()
            await asyncio.gather(asyncio.Future())

    async def stop(self) -> None:
        logger.info("Stopping DesktopServer...")
        self.scheduler.stop()
        if hasattr(self, "server"):
            self.server.close()
            await self.server.wait_closed()

    async def _handle_client(self, ws: ServerConnection) -> None:
        self._clients.add(ws)
        logger.info("Client connected. Total clients: %d", len(self._clients))
        try:
            async for message in ws:
                if isinstance(message, str):
                    await self._handle_jsonrpc(ws, message)
                elif isinstance(message, bytes):
                    if ws in self._voice_buffers:
                        self._voice_buffers[ws].extend(message)
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            self._voice_buffers.pop(ws, None)
            logger.info("Client disconnected. Total clients: %d", len(self._clients))

    async def _handle_jsonrpc(self, ws: ServerConnection, raw: str) -> None:
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_error(ws, None, JSONRPC_PARSE_ERROR, "Invalid JSON")
            return

        method = request.get("method", "")
        params = request.get("params") or {}
        req_id = request.get("id")

        try:
            result = await self._dispatch(ws, method, params)
        except KeyError:
            await self._send_error(ws, req_id, JSONRPC_METHOD_NOT_FOUND, f"Method not found: {method}")
            return
        except Exception as exc:
            logger.exception("Error handling method %s", method)
            await self._send_error(ws, req_id, JSONRPC_INTERNAL_ERROR, str(exc))
            return

        if req_id is not None:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}, ensure_ascii=False))

    async def _dispatch(self, ws: ServerConnection, method: str, params: dict[str, Any]) -> Any:
        match method:
            case "chat.send":
                text = params["text"]
                context_data = params.get("context", {})
                if isinstance(context_data, dict) and "screen_analysis" in context_data:
                    summary = context_data["screen_analysis"].get("summary", "")
                    if summary:
                        text = f"[Screen Analysis Context:\n{summary}]\n\nUser Question: {text}"
                conv = Conversation(provider="desktop", model="default")
                conv.add(Role.USER, text)
                
                async def on_stream(chunk):
                    chunk_data = chunk.model_dump() if hasattr(chunk, "model_dump") else str(chunk)
                    await self._broadcast("chat.stream", {"chunk": chunk_data})
                    
                async def run_chat():
                    try:
                        reply = await self.runtime.chat(conv, stream_callback=on_stream)
                        await self._broadcast("chat.done", {"reply": reply})
                    except Exception as e:
                        logger.exception("Error in chat")
                        await self._broadcast("chat.error", {"error": str(e)})
                        
                asyncio.create_task(run_chat())
                return {"status": "started"}
                
            case "task.submit":
                goal = params["text"]
                conv = Conversation(provider="desktop", model="default")
                
                async def run_bg():
                    try:
                        async for event in self.runtime.run_mission(goal, conv):
                            logger.info("Mission event: %s", event)
                            event_data = event.model_dump() if hasattr(event, "model_dump") else str(event)
                            await self._broadcast("task.event", {"task_id": "mission-1", "event": event_data})
                        await self._broadcast("task.done", {"task_id": "mission-1"})
                    except Exception as e:
                        logger.exception("Error in mission")
                        await self._broadcast("task.error", {"task_id": "mission-1", "error": str(e)})
                        
                asyncio.create_task(run_bg())
                return {"task_id": "mission-1", "status": "started"}
                
            case "action.confirm":
                action_id = params.get("confirm_id")
                approved = params.get("approved", False)
                self.runtime.permission_gate.confirm(action_id, approved)
                return {"confirmed": True}
                
            case "voice.ptt_start":
                self._voice_buffers[ws] = bytearray()
                return {"status": "recording"}
                
            case "voice.ptt_stop":
                buffer = self._voice_buffers.pop(ws, bytearray())
                if not buffer:
                    return {"reply": "No audio received"}
                
                if self.stt_engine is None:
                    from aios.config.settings import Settings
                    from aios.desktop.voice.stt import SpeechToTextEngine
                    settings = Settings.load()
                    self.stt_engine = SpeechToTextEngine(
                        model_size=settings.voice.stt.model_size,
                        language=settings.voice.stt.language,
                        device=settings.voice.stt.device
                    )
                
                try:
                    text = await self.stt_engine.transcribe(bytes(buffer))
                    if not text:
                        return {"reply": "Could not transcribe audio"}
                        
                    # Auto-forward to chat engine
                    await self._dispatch(ws, "chat.send", {"text": text})
                    return {"reply": text}
                except Exception as e:
                    logger.error("Failed to transcribe: %s", e)
                    return {"reply": f"Error: {str(e)}"}
                
            case "vision.analyze_image":
                img_b64 = params.get("image_base64", "")
                logger.info("Received vision.analyze_image request (length: %d)", len(img_b64))
                return {
                    "summary": "Screen capture processed successfully",
                    "windows": [],
                    "text": [],
                    "status": "success",
                }

            case "vision.capture":
                try:
                    import io
                    from PIL import ImageGrab
                    screenshot = ImageGrab.grab()
                    buf = io.BytesIO()
                    screenshot.save(buf, format="PNG")
                    import base64
                    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                    return {"status": "success", "image_base64": b64_str}
                except Exception as e:
                    logger.error("Vision capture failed: %s", e)
                    return {"status": "error", "message": str(e)}

            case "tools.list":
                from aios.desktop.schemas import ToolItem, ToolsListResponse
                if hasattr(self.runtime, "executor") and self.runtime.executor:
                    tools = [
                        ToolItem(name=t.name, description=t.description)
                        for t in self.runtime.executor.tool_registry.list()
                    ]
                    return ToolsListResponse(tools=tools).model_dump()
                return ToolsListResponse().model_dump()

            case "memory.store":
                content = params.get("content")
                category = params.get("category", "fact")
                importance = params.get("importance", 5)
                tags = params.get("tags", [])
                long_term = self.runtime.memory_orchestrator.long_term
                new_id = long_term.store(content, category, importance, tags)
                return {"status": "success", "id": new_id}

            case "memory.list":
                limit = params.get("limit", 20)
                category = params.get("category")
                long_term = self.runtime.memory_orchestrator.long_term
                results = long_term.recall_recent(limit=limit, category=category)
                return {"results": results}

            case "memory.search":
                query = params.get("query")
                limit = params.get("limit", 20)
                category = params.get("category")
                long_term = self.runtime.memory_orchestrator.long_term
                results = long_term.recall(query, limit=limit, category=category)
                return {"results": results}

            case "memory.delete":
                memory_id = params.get("id")
                long_term = self.runtime.memory_orchestrator.long_term
                success = long_term.forget(memory_id)
                return {"status": "success", "deleted": success}
                
            case "timer.create":
                label = params.get("label", "Timer")
                duration = params.get("duration_sec", 60)
                engine = self.runtime._timer_engine
                tid = engine.create_timer(label, duration)
                return {"status": "success", "id": tid}

            case "timer.stopwatch":
                label = params.get("label", "Stopwatch")
                engine = self.runtime._timer_engine
                tid = engine.create_stopwatch(label)
                return {"status": "success", "id": tid}

            case "timer.alarm":
                label = params.get("label", "Alarm")
                target_time = params.get("target_time")
                engine = self.runtime._timer_engine
                tid = engine.create_alarm(label, target_time)
                return {"status": "success", "id": tid}

            case "timer.list":
                engine = self.runtime._timer_engine
                return {"results": engine.get_all()}

            case "timer.action":
                action = params.get("action")
                tid = params.get("id")
                engine = self.runtime._timer_engine
                success = False
                if action == "pause":
                    success = engine.pause(tid)
                elif action == "resume":
                    success = engine.resume(tid)
                elif action == "stop":
                    success = engine.stop(tid)
                elif action == "delete":
                    success = engine.delete(tid)
                return {"status": "success", "success": success}

            case "calendar.add":
                title = params.get("title")
                start_time = params.get("start_time")
                end_time = params.get("end_time")
                description = params.get("description", "")
                all_day = params.get("all_day", False)
                category = params.get("category", "general")
                engine = self.runtime._calendar_engine
                new_id = engine.add_event(title, start_time, end_time, description, all_day, category)
                return {"status": "success", "id": new_id}

            case "calendar.get":
                date_from = params.get("date_from")
                date_to = params.get("date_to")
                engine = self.runtime._calendar_engine
                results = engine.get_events(date_from, date_to)
                return {"results": results}

            case "calendar.upcoming":
                hours = params.get("hours", 24)
                engine = self.runtime._calendar_engine
                results = engine.get_upcoming(hours)
                return {"results": results}

            case "calendar.delete":
                event_id = params.get("id")
                engine = self.runtime._calendar_engine
                success = engine.delete_event(event_id)
                return {"status": "success", "deleted": success}

            case "calendar.update":
                event_id = params.get("id")
                engine = self.runtime._calendar_engine
                
                update_data = {}
                for k in ["title", "start_time", "end_time", "description", "all_day", "category"]:
                    if k in params:
                        update_data[k] = params[k]
                
                if update_data:
                    success = engine.update_event(event_id, **update_data)
                    return {"status": "success", "updated": success}
                return {"status": "error", "error": "No fields to update"}
                
            case "vision.capture":
                import base64

                from aios.desktop.vision.capture import capture_screen_png
                png_bytes = await capture_screen_png()
                return {"image_base64": base64.b64encode(png_bytes).decode('ascii')}
                
            case "vision.analyze_image":
                image_b64 = params.get("image_base64", "")
                if not image_b64:
                    return {"error": "image_base64 not provided"}
                try:
                    png_bytes = _decode_base64_png(image_b64)
                except Exception as exc:
                    return {"error": f"Failed to decode PNG: {exc}"}
                
                analysis = await self.vision.analyze(png_bytes)
                data = analysis.model_dump()
                data["summary"] = _build_screen_summary(data)
                return data
                
            case "fs.list":
                root = Path(params.get("path", ".")).resolve()
                if not root.is_dir():
                    return {"error": "Not a directory", "entries": []}
                entries = []
                for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    try:
                        stat = child.stat()
                        entries.append({
                            "name": child.name,
                            "is_dir": child.is_dir(),
                            "size": stat.st_size if child.is_file() else 0,
                            "modified": stat.st_mtime,
                        })
                    except OSError:
                        continue
                return {"path": str(root), "entries": entries}
                
            case "fs.read":
                target = Path(params["path"]).resolve()
                if not target.is_file():
                    return {"error": "File not found"}
                content = target.read_text(encoding="utf-8", errors="replace")
                return {"name": target.name, "content": content, "size": target.stat().st_size}
                
            case "system.status":
                from aios.desktop.schemas import SystemStatusCore, SystemStatusResponse
                tool_count = len(self.runtime.executor.tool_registry.list()) if hasattr(self.runtime, "executor") and self.runtime.executor else 0
                return SystemStatusResponse(
                    core=SystemStatusCore(ok=True, detail="aios-cli runtime loaded"),
                    tools=tool_count,
                    modules={},
                ).model_dump()
                
            case "conversation.list":
                return []
            case "conversation.create":
                import uuid
                return {"id": str(uuid.uuid4()), "title": "New Chat"}
            case "conversation.get":
                return {"messages": []}
            case "timeline.history":
                return []
            case "settings.get":
                try:
                    from aios.config.settings import Settings
                    return Settings.load().model_dump()
                except Exception as e:
                    logger.error(f"Failed to load settings: {e}")
                    return {}
            case "settings.update":
                try:
                    from aios.cli.main import get_provider_and_model
                    from aios.config.settings import update_default_settings
                    
                    provider = params.get("default_provider")
                    model = params.get("default_model")
                    
                    if provider or model:
                        update_default_settings(provider=provider, model=model)
                        provider_obj, _, provider_name, model_name = get_provider_and_model(provider, model)
                        self.runtime._config.provider = provider_obj
                        logger.info(f"Updated runtime provider to {provider_name}/{model_name}")
                    
                    return {"success": True}
                except Exception as e:
                    logger.error(f"Failed to update settings: {e}")
                    return {"success": False, "error": str(e)}
            case "llm.models":
                try:
                    models = []
                    if self.runtime._config and self.runtime._config.provider:
                        if hasattr(self.runtime._config.provider, "list_models"):
                            models = await self.runtime._config.provider.list_models()
                    return {"models": models}
                except Exception as e:
                    logger.error(f"Failed to get models: {e}")
                    return {"models": [], "error": str(e)}
            case "providers.list":
                try:
                    from aios.config.settings import Settings
                    settings = Settings.load()
                    provs = []
                    for name, cfg in settings.providers.items():
                        prov = cfg.model_dump()
                        prov["name"] = name
                        provs.append(prov)
                    if not any(p["name"] == "ollama" for p in provs):
                        provs.append({"name": "ollama", "base_url": "http://localhost:11434"})
                    return {"providers": provs}
                except Exception:
                    return {"providers": [{"name": "ollama", "base_url": "http://localhost:11434"}]}
            case _:
                raise KeyError(method)

    async def _send_error(self, ws: ServerConnection, req_id: Any, code: int, message: str) -> None:
        await ws.send(json.dumps(
            {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}},
            ensure_ascii=False,
        ))

def _decode_base64_png(b64: str) -> bytes:
    import base64
    if "," in b64 and b64.lstrip().startswith("data:"):
        b64 = b64.split(",", 1)[1]
    return base64.b64decode(b64)

def _build_screen_summary(data: dict[str, Any]) -> str:
    summary_parts: list[str] = []
    windows = data.get("windows", [])
    buttons = data.get("buttons", [])
    texts = data.get("text", [])

    if windows:
        summary_parts.append(f"Windows ({len(windows)}):")
        for w in windows[:10]:
            title = w.get("title", "?")
            x, y = w.get("left", w.get("x", 0)), w.get("top", w.get("y", 0))
            w_, h = w.get("width", 0), w.get("height", 0)
            summary_parts.append(f"  - {title} at ({x},{y}) {w_}x{h}")

    if texts:
        summary_parts.append(f"\\nDetected text ({len(texts)}):")
        for t in texts[:30]:
            summary_parts.append(f"  - {t.get('text', '')[:100]}")

    return "\\n".join(summary_parts) if summary_parts else "No UI elements detected on screen."
