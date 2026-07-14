from __future__ import annotations


class TokenBudget:
    """
    Tracks and limits token usage for a conversation.
    """
    def __init__(self, limit: int = 128000) -> None:
        self.limit = limit
        self.current_usage = 0

    def add_tokens(self, count: int) -> None:
        self.current_usage += count

    def subtract_tokens(self, count: int) -> None:
        self.current_usage -= count

    @property
    def usage_percentage(self) -> float:
        return (self.current_usage / self.limit) * 100

    def is_over_budget(self) -> bool:
        return self.current_usage >= self.limit
