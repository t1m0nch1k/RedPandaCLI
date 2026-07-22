from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class TimerTool(Tool):
    name = "timer_tool"
    description = (
        "Manage timers, stopwatches, and alarms. Use this to track time "
        "or remind the user about something after a specific duration."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start_timer", "start_stopwatch", "start_alarm", "pause", "resume", "stop", "delete", "list"],
                "description": "The action to perform",
            },
            "label": {
                "type": "string",
                "description": "Label for the timer (e.g. 'Boil eggs')",
            },
            "duration_sec": {
                "type": "integer",
                "description": "Duration in seconds (required for 'start_timer')",
            },
            "target_time": {
                "type": "string",
                "description": "Target time ISO 8601 (required for 'start_alarm')",
            },
            "timer_id": {
                "type": "string",
                "description": "ID of the timer to pause/resume/stop/delete",
            }
        },
        "required": ["action"],
    }

    def __init__(self, timer_engine: Any):
        super().__init__()
        self.timer_engine = timer_engine

    async def run(
        self,
        action: str,
        label: str = "Timer",
        duration_sec: int = 0,
        target_time: str = "",
        timer_id: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        if action == "start_timer":
            if duration_sec <= 0:
                return ToolResult(success=False, error="duration_sec must be > 0")
            tid = self.timer_engine.create_timer(label, duration_sec)
            return ToolResult(success=True, output=f"Timer '{label}' started. ID: {tid}")

        elif action == "start_stopwatch":
            tid = self.timer_engine.create_stopwatch(label)
            return ToolResult(success=True, output=f"Stopwatch '{label}' started. ID: {tid}")

        elif action == "start_alarm":
            if not target_time:
                return ToolResult(success=False, error="target_time is required")
            tid = self.timer_engine.create_alarm(label, target_time)
            return ToolResult(success=True, output=f"Alarm '{label}' set. ID: {tid}")

        elif action == "pause":
            if not timer_id:
                return ToolResult(success=False, error="timer_id is required")
            if self.timer_engine.pause(timer_id):
                return ToolResult(success=True, output=f"Timer {timer_id} paused.")
            return ToolResult(success=False, error="Timer not found or not running.")

        elif action == "resume":
            if not timer_id:
                return ToolResult(success=False, error="timer_id is required")
            if self.timer_engine.resume(timer_id):
                return ToolResult(success=True, output=f"Timer {timer_id} resumed.")
            return ToolResult(success=False, error="Timer not found or not paused.")

        elif action == "stop":
            if not timer_id:
                return ToolResult(success=False, error="timer_id is required")
            if self.timer_engine.stop(timer_id):
                return ToolResult(success=True, output=f"Timer {timer_id} stopped.")
            return ToolResult(success=False, error="Timer not found.")

        elif action == "delete":
            if not timer_id:
                return ToolResult(success=False, error="timer_id is required")
            if self.timer_engine.delete(timer_id):
                return ToolResult(success=True, output=f"Timer {timer_id} deleted.")
            return ToolResult(success=False, error="Timer not found.")

        elif action == "list":
            timers = self.timer_engine.get_all()
            if not timers:
                return ToolResult(success=True, output="No active timers.")
            lines = []
            for t in timers:
                lines.append(
                    f"[{t['id']}] {t['label']} ({t['type']}) - state: {t['state']}, "
                    f"remaining: {t['remaining_sec']:.1f}s, elapsed: {t['elapsed_sec']:.1f}s"
                )
            return ToolResult(success=True, output="\n".join(lines))

        return ToolResult(success=False, error=f"Unknown action {action}")
