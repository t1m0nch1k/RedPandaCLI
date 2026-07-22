"""Асинхронный IPC-клиент к ядру AIOS (WebSocket JSON-RPC 2.0).

Работает в отдельном потоке со своим asyncio event-loop (основной поток занят
PySide6 GUI-loop). Связь с GUI-потоком — через thread-safe ``queue.Queue`` для
исходящих запросов и колбэки ``on_settings_updated`` / ``on_reply`` для входящих.
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

log = logging.getLogger("aios.overlay.ipc")


class IPCRequest:
    """Исходящий JSON-RPC запрос."""

    __slots__ = ("method", "params", "future")

    def __init__(self, method: str, params: dict[str, Any] | None = None) -> None:
        self.method = method
        self.params = params or {}
        self.future: asyncio.Future[dict[str, Any]] | None = None


class OverlayIPC:
    """Обёртка над WebSocket-подключением к ядру."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        on_settings_updated: Callable[[dict[str, Any]], None] | None = None,
        on_reply: Callable[[str, dict[str, Any]], None] | None = None,
        on_cursor_preview: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self._on_settings_updated = on_settings_updated
        self._on_reply = on_reply
        self._on_cursor_preview = on_cursor_preview
        self._send_queue: queue.Queue[IPCRequest | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        """Запустить IPC-клиент в фоновом потоке (неблокирующе)."""
        self._thread = threading.Thread(target=self._run, name="aios-overlay-ipc", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Остановить клиент."""
        self._stop.set()
        self._send_queue.put(None)  # разблокировать ожидание
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(self._cancel_all)
            except RuntimeError:
                pass
        if self._thread:
            self._thread.join(timeout=2)

    def _cancel_all(self) -> None:
        pass

    # ----------------------------------------------------------- thread-side

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._connect_loop())
        except Exception:  # noqa: BLE001
            log.exception("IPC-цикл упал")
        finally:
            loop.close()
            self._loop = None

    async def _connect_loop(self) -> None:
        """Бесконечный цикл с автореконнектом."""
        import websockets

        backoff = 1.0
        while not self._stop.is_set():
            try:
                log.info("Подключение к ядру %s ...", self.url)
                async with websockets.connect(self.url, max_size=10_485_760) as ws:
                    log.info("Подключено к ядру AIOS")
                    backoff = 1.0
                    await self._session(ws)
            except Exception as exc:  # noqa: BLE001
                if not self._stop.is_set():
                    log.warning("Подключение к ядру не удалось (%s); повтор через %.0fs", exc, backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 1.5, 10.0)

    async def _session(self, ws: Any) -> None:
        """Активная сессия: читаем входящие + отправляем исходящие."""
        pending: dict[int, IPCRequest] = {}
        next_id = 1

        async def _reader() -> None:
            try:
                async for raw in ws:
                    if isinstance(raw, bytes):
                        continue
                    msg = json.loads(raw)
                    req_id = msg.get("id")
                    method = msg.get("method")
                    if req_id is None and method:
                        if method == "event":
                            self._handle_event(msg.get("params", {}))
                        elif self._on_reply:
                            self._on_reply(method, msg.get("params", {}))
                        continue

                    # Ответ на запрос
                    if req_id is not None and req_id in pending:
                        req = pending.pop(req_id)
                        result = msg.get("result") or {"error": msg.get("error")}
                        if self._on_reply:
                            self._on_reply(req.method, result)
                        if req.future and not req.future.done():
                            req.future.set_result(result)
            except Exception:  # noqa: BLE001
                log.exception("Reader упал")

        async def _sender() -> None:
            while not self._stop.is_set():
                try:
                    req = await asyncio.get_event_loop().run_in_executor(
                        None, self._send_queue.get, True, 0.25
                    )
                except queue.Empty:
                    continue
                if req is None:
                    return
                nonlocal_next = _allocate_id()
                req_id = nonlocal_next
                pending[req_id] = req
                payload = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": req.method,
                    "params": req.params,
                }
                try:
                    await ws.send(json.dumps(payload, ensure_ascii=False))
                except Exception:  # noqa: BLE001
                    log.exception("Отправка не удалась: %s", req.method)
                    pending.pop(req_id, None)
                    if req.future and not req.future.done():
                        req.future.set_result({"error": "send failed"})

        next_id_box = [1]

        def _allocate_id() -> int:
            i = next_id_box[0]
            next_id_box[0] += 1
            return i

        # Запускаем reader и sender параллельно
        await asyncio.wait(
            [
                asyncio.ensure_future(_reader()),
                asyncio.ensure_future(_sender()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )

    def _handle_event(self, params: dict[str, Any]) -> None:
        """Диспатч входящего события ядра."""
        event = params.get("event")
        payload = params.get("payload", {})
        if event == "settings.updated":
            if self._on_settings_updated:
                self._on_settings_updated(payload)
        elif event == "cursor.preview":
            if self._on_cursor_preview:
                self._on_cursor_preview(payload)
        elif event == "log" and payload.get("level") in ("error", "critical"):
            log.info("[kernel] %s", payload.get("message", ""))

    # ----------------------------------------------------------- public API

    def call(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Отправить fire-and-forget запрос (ответ придёт в on_reply)."""
        self._send_queue.put(IPCRequest(method, params))

    async def call_async(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Отправить запрос и дождаться ответа. Должен вызываться из IPC-потока."""
        req = IPCRequest(method, params)
        req.future = asyncio.get_event_loop().create_future()
        self._send_queue.put(req)
        return await asyncio.wait_for(req.future, timeout=30)

    def call_from_gui(
        self, method: str, params: dict[str, Any] | None = None
    ) -> None:
        """Отправить запрос из GUI-потока (fire-and-forget)."""
        self._send_queue.put(IPCRequest(method, params))
