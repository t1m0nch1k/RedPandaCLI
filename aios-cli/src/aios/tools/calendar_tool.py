from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class CalendarTool(Tool):
    name = "calendar_tool"
    description = (
        "Interact with the user's calendar. Use this to schedule events, get upcoming events, "
        "or manage calendar items."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "get", "upcoming", "delete", "update"],
                "description": "The action to perform",
            },
            "title": {
                "type": "string",
                "description": "Title of the event (required for 'add')",
            },
            "start_time": {
                "type": "string",
                "description": "Start time in ISO 8601 format (required for 'add')",
            },
            "end_time": {
                "type": "string",
                "description": "End time in ISO 8601 format",
            },
            "description": {
                "type": "string",
                "description": "Description of the event",
            },
            "date_from": {
                "type": "string",
                "description": "Start date for 'get' action (ISO 8601)",
            },
            "date_to": {
                "type": "string",
                "description": "End date for 'get' action (ISO 8601)",
            },
            "event_id": {
                "type": "integer",
                "description": "ID of the event (required for 'delete', 'update')",
            },
            "hours": {
                "type": "integer",
                "description": "Hours ahead to check for 'upcoming' action (default 24)",
            }
        },
        "required": ["action"],
    }

    def __init__(self, calendar_engine: Any):
        super().__init__()
        self.calendar_engine = calendar_engine

    async def run(
        self,
        action: str,
        title: str = "",
        start_time: str = "",
        end_time: str | None = None,
        description: str = "",
        date_from: str = "",
        date_to: str = "",
        event_id: int = 0,
        hours: int = 24,
        **kwargs: Any,
    ) -> ToolResult:
        if action == "add":
            if not title or not start_time:
                return ToolResult(success=False, error="title and start_time are required for add")
            new_id = self.calendar_engine.add_event(
                title=title, start_time=start_time, end_time=end_time, description=description
            )
            return ToolResult(success=True, output=f"Added calendar event '{title}' with ID {new_id}")
            
        elif action == "get":
            if not date_from or not date_to:
                return ToolResult(success=False, error="date_from and date_to required for get")
            results = self.calendar_engine.get_events(date_from, date_to)
            return ToolResult(success=True, output=self._format_results(results))
            
        elif action == "upcoming":
            results = self.calendar_engine.get_upcoming(hours=hours)
            return ToolResult(success=True, output=self._format_results(results))
            
        elif action == "delete":
            if not event_id:
                return ToolResult(success=False, error="event_id required for delete")
            success = self.calendar_engine.delete_event(event_id)
            if success:
                return ToolResult(success=True, output=f"Deleted event {event_id}")
            return ToolResult(success=False, error=f"Event {event_id} not found")
            
        elif action == "update":
            if not event_id:
                return ToolResult(success=False, error="event_id required for update")
            # We can use kwargs to update arbitrary fields that were passed.
            # But the schema doesn't define arbitrary kwargs properly for update. 
            # So let's manually extract standard ones if provided.
            update_data = {}
            if title:
                update_data["title"] = title
            if start_time:
                update_data["start_time"] = start_time
            if end_time:
                update_data["end_time"] = end_time
            if description:
                update_data["description"] = description
            
            if not update_data:
                return ToolResult(success=False, error="No fields provided to update")
                
            success = self.calendar_engine.update_event(event_id, **update_data)
            if success:
                return ToolResult(success=True, output=f"Updated event {event_id}")
            return ToolResult(success=False, error=f"Event {event_id} not found")

        return ToolResult(success=False, error=f"Unknown action {action}")

    def _format_results(self, results: list[dict[str, Any]]) -> str:
        if not results:
            return "No events found."
        
        lines = []
        for r in results:
            lines.append(f"[{r['id']}] {r['start_time']} - {r['title']}")
            if r.get('end_time'):
                lines.append(f"  End: {r['end_time']}")
            if r.get('description'):
                lines.append(f"  Description: {r['description']}")
        return "\n".join(lines)
