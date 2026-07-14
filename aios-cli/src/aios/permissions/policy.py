from __future__ import annotations

from aios.permissions.base import PermissionDecision
from aios.permissions.rules import PermissionRule


class PermissionPolicy:
    """
    A collection of rules that defines the permission behavior for the system.
    """
    def __init__(self, name: str, rules: list[PermissionRule]) -> None:
        self.name = name
        self.rules = rules

    def evaluate(self, tool_name: str, args: dict[str, Any]) -> PermissionDecision:
        # Rules are evaluated in order. The first matching rule wins.
        for rule in self.rules:
            if rule.matches(tool_name, args):
                return rule.decision
        
        # Default fallback
        return PermissionDecision.ASK
