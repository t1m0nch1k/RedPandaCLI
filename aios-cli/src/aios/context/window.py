from __future__ import annotations

from typing import Any


class ContextWindow:
    """
    Estimates token counts for messages and conversation history.
    """
    def __init__(self, model_name: str = "unknown") -> None:
        self.model_name = model_name

    def estimate_tokens(self, text: str) -> int:
        """
        Provides a heuristic estimation of tokens. 
        In a production environment, this would use tiktoken or model-specific tokenizers.
        """
        if not text:
            return 0
        
        # Heuristic: ~4 characters per token for English
        # We use a more conservative estimate for mixed content
        return len(text) // 3

    def estimate_message_tokens(self, role: str, content: str) -> int:
        # Base overhead for message structure
        overhead = 4 
        return overhead + self.estimate_tokens(content)

    def total_tokens(self, messages: list[Any]) -> int:
        def _role(m):
            return m.role.value if hasattr(m, "role") else m.get("role", "user")
        def _content(m):
            return m.content if hasattr(m, "content") else m.get("content", "")
        return sum(self.estimate_message_tokens(_role(m), _content(m)) for m in messages)
