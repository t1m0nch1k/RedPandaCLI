import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

class ProactiveScheduler:
    def __init__(self, server: Any, runtime: Any):
        self.server = server
        self.runtime = runtime
        self._task = None

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self.run_loop())

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None

    async def run_loop(self):
        while True:
            try:
                await self._check_timers()
                await self._check_calendar()
                await asyncio.sleep(5)  # Check every 5 seconds for timers
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)

    async def _check_timers(self):
        if not hasattr(self.runtime, "_timer_engine"):
            return
            
        expired = self.runtime._timer_engine.check_expired()
        for t in expired:
            if t.state == "finished":
                # Ensure we only alert once by deleting or marking alerted.
                # Actually, check_expired() sets state to finished. 
                # Wait, if it's finished, it might be returned again if we don't remove it or mark it?
                # Let's remove it to avoid repeat alerts.
                self.runtime._timer_engine.delete(t.id)
                await self._on_trigger("timer", {"label": t.label, "type": t.type})

    async def _check_calendar(self):
        if not hasattr(self.runtime, "_calendar_engine"):
            return
            
        # Get upcoming in the next 15 mins
        # This requires more complex state tracking (did we remind them already?)
        # For MVP, let's keep it simple or rely on timers for now.
        pass

    async def _on_trigger(self, trigger_type: str, data: dict):
        message = ""
        if trigger_type == "timer":
            t = data.get("type", "timer")
            label = data.get("label", "")
            if t == "alarm":
                message = f"Alarm '{label}' is ringing!"
            else:
                message = f"Timer '{label}' has finished!"
        
        # Broadcast to client
        if hasattr(self.server, "_broadcast"):
            await self.server._broadcast("agent.proactive", {
                "trigger": trigger_type,
                "message": message,
                "data": data,
            })
