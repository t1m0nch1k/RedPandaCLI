from __future__ import annotations

from typing import Any

from aios.context.budget import TokenBudget
from aios.context.compactor import Compactor
from aios.context.window import ContextWindow


class ContextManager:
    """
    Orchestrates token tracking, compaction, and history management.
    """
    def __init__(
        self, 
        model_name: str, 
        token_limit: int = 128000
    ) -> None:
        self.window = ContextWindow(model_name)
        self.budget = TokenBudget(token_limit)
        self.compactor = Compactor(self.window)

    def update_usage(self, messages: list[Any]) -> None:
        """Updates the current token budget based on the conversation history."""
        self.budget.current_usage = self.window.total_tokens(messages)

    async def manage(self, conversation: Any, provider: Any, force_sweep: bool = False) -> None:
        """
        Analyzes current context and applies compaction if budget is exceeded or force_sweep is True.
        """
        self.update_usage(conversation.messages)
        
        if force_sweep or self.budget.usage_percentage > 80:
            # First, try to compact by summarizing tool outputs
            conversation.messages = self.compactor.summarize_successful_tools(conversation.messages)
            self.update_usage(conversation.messages)
            
            # If still over 80%, do a hard summarization of the first half
            if self.budget.usage_percentage > 80:
                summary = await self.compactor.summarize(conversation.messages, provider)
                
                # Replace old messages with a single summary message
                split_idx = len(conversation.messages) // 2
                old_messages = conversation.messages[:split_idx]
                remaining_messages = conversation.messages[split_idx:]
                
                # Update conversation (assuming conversation.messages is a list we can modify or replace)
                from aios.core.models import Message, Role
                conversation.messages = [Message(role=Role.SYSTEM, content=f"Summary of previous conversation: {summary}")] + remaining_messages
                
                # Update usage after compaction
                self.update_usage(conversation.messages)
