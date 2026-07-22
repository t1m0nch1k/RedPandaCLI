from __future__ import annotations

from typing import Any

from aios.context.window import ContextWindow


class Compactor:
    """
    Implements strategies for compressing conversation history.
    """
    def __init__(self, window: ContextWindow) -> None:
        self.window = window

    async def summarize(self, messages: list[Any], provider: Any) -> str:
        """
        Uses the LLM to summarize the oldest part of the conversation.
        """
        # We summarize the first 50% of the messages (skipping system/first user message ideally)
        split_idx = len(messages) // 2
        to_summarize = messages[:split_idx]
        
        def _role(m):
            return m.role.value if hasattr(m, "role") else m.get("role", "user")
        def _content(m):
            return m.content if hasattr(m, "content") else m.get("content", "")
        summary_text = ""
        for msg in to_summarize:
            summary_text += f"{_role(msg)}: {_content(msg)}\n"

        prompt = f"Summarize the following conversation history concisely, preserving key technical decisions and facts:\n\n{summary_text}"
        
        # Call the provider for a concise summary
        summary = await provider.complete([{"role": "user", "content": prompt}])
        return summary

    def truncate_tool_result(self, content: str, max_tokens: int = 2000) -> tuple[str, bool]:
        """
        Truncates large tool results and adds a note about the truncation.
        """
        estimated = self.window.estimate_tokens(content)
        if estimated <= max_tokens:
            return content, False
            
        # Truncate to max_tokens * ~3 chars
        truncated = content[:max_tokens * 3] + "\n\n[... Output truncated. Use read_file_range or similar tools to see more ...]"
        return truncated, True

    def summarize_successful_tools(self, messages: list[Any]) -> list[Any]:
        """
        Intelligently evicts context by summarizing successful tool outputs (e.g. multi_edit, replace_text)
        that don't need to be fully kept in context, while preserving the tool call and basic success notification.
        """
        from aios.core.models import Role
        
        new_messages = []
        for msg in messages:
            role = msg.role if hasattr(msg, "role") else Role(msg.get("role", "user"))
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            
            # If it's a successful tool execution with a very large output that isn't read_file or similar
            if role == Role.TOOL and "success=True" in content.replace("'", "").replace('"', ""):
                # We can compress the output of file modification tools
                name = getattr(msg, "name", "")
                if name in ["multi_edit", "replace_text", "patch", "write_to_file", "shell"]:
                    # Keep only the confirmation, strip huge diffs or outputs
                    if len(content) > 200:
                        content = f"Tool '{name}' succeeded. (Output hidden to save context)"
                        # If msg is an object, update it, otherwise create new
                        if hasattr(msg, "content"):
                            msg.content = content
                        else:
                            msg["content"] = content
            
            new_messages.append(msg)
            
        return new_messages
