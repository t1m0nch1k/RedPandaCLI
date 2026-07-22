from __future__ import annotations

import os
import re
from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool
from aios.workspace import WorkspaceContext


class TaskManagerTool(Tool):
    name = "task_manager"
    description = (
        "Create, read, and update task plans in Markdown format. "
        "Helps the agent track progress across long sessions by easily updating task statuses."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "read", "update_status"],
                "description": "Action to perform",
            },
            "path": {
                "type": "string",
                "description": "Path to the plan file (e.g., '.aios/plan.md')",
            },
            "content": {
                "type": "string",
                "description": "Content of the plan (for 'create' action). Should be a markdown list with checkboxes like '- [ ] Task 1'",
            },
            "task_id": {
                "type": "string",
                "description": "The exact or partial text of the task to update (for 'update_status' action).",
            },
            "status": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "description": "New status for the task (for 'update_status' action)",
            },
        },
        "required": ["action", "path"],
    }

    def __init__(self, workspace: WorkspaceContext | None = None) -> None:
        self.workspace = workspace or WorkspaceContext.from_cwd()

    async def run(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        path = kwargs.get("path")
        
        if not path:
            return ToolResult(success=False, error="path is required")

        full_path = self.workspace.get_absolute_path(path)

        if action == "create":
            content = kwargs.get("content", "")
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, output=f"Plan created at {path}")

        elif action == "read":
            if not os.path.exists(full_path):
                return ToolResult(success=False, error=f"Plan file not found: {path}")
            with open(full_path, encoding="utf-8") as f:
                return ToolResult(success=True, output=f.read())

        elif action == "update_status":
            task_id = kwargs.get("task_id")
            if not task_id:
                return ToolResult(success=False, error="task_id is required for update_status action")
                
            status_mapping = {"todo": "[ ]", "in_progress": "[/]", "done": "[x]"}
            status_str = status_mapping.get(kwargs.get("status", "done"), "[x]")

            if not os.path.exists(full_path):
                return ToolResult(success=False, error=f"Plan file not found: {path}")

            with open(full_path, encoding="utf-8") as f:
                lines = f.readlines()

            updated = False
            for i, line in enumerate(lines):
                # Search for task_id (case insensitive) and see if line contains a markdown checkbox
                if task_id.lower() in line.lower() and re.search(r"-\s+\[[ x/]+\]", line):
                    lines[i] = re.sub(r"-\s+\[[ x/]+\]", f"- {status_str}", line, count=1)
                    updated = True
                    break

            if not updated:
                return ToolResult(success=False, error=f"Task '{task_id}' not found in {path}")

            with open(full_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            return ToolResult(success=True, output=f"Updated task '{task_id}' status to {status_str} in {path}")

        return ToolResult(success=False, error=f"Unknown action: {action}")
