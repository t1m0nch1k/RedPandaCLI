from __future__ import annotations

from aios.permissions.base import PermissionDecision
from aios.permissions.policy import PermissionPolicy
from aios.permissions.rules import PermissionRule


def get_trusted_policy() -> PermissionPolicy:
    """
    The 'trusted' profile: most read actions are allowed, modifications are asked.
    """
    return PermissionPolicy(
        name="trusted",
        rules=[
            # Read-only tools are generally allowed
            PermissionRule(tool="filesystem", action="read_file", decision=PermissionDecision.ALLOW),
            PermissionRule(tool="filesystem", action="list_files", decision=PermissionDecision.ALLOW),
            PermissionRule(tool="filesystem", action="search_text", decision=PermissionDecision.ALLOW),
            PermissionRule(tool="environment", action="read", decision=PermissionDecision.ALLOW),
            # Modification tools are asked
            PermissionRule(tool="shell", decision=PermissionDecision.ASK),
            PermissionRule(tool="git", decision=PermissionDecision.ASK),
            PermissionRule(tool="filesystem", action="replace_text", decision=PermissionDecision.ASK),
            PermissionRule(tool="filesystem", action="create_file", decision=PermissionDecision.ASK),
            PermissionRule(tool="filesystem", action="delete", decision=PermissionDecision.ASK),
        ]
    )

def get_strict_policy() -> PermissionPolicy:
    """
    The 'strict' profile: everything is asked.
    """
    return PermissionPolicy(
        name="strict",
        rules=[] # Falls back to ASK
    )

def get_yolo_policy() -> PermissionPolicy:
    """
    The 'yolo' profile: everything is allowed.
    """
    return PermissionPolicy(
        name="yolo",
        rules=[
            PermissionRule(tool="any", decision=PermissionDecision.ALLOW)
        ]
    )
# Fix for get_yolo_policy to actually match everything
def _yolo_match_all(tool_name: str, args: dict) -> bool:
    return True

# Redefining get_yolo_policy properly
def get_yolo_policy_fixed() -> PermissionPolicy:
    class AnyRule(PermissionRule):
        def matches(self, tool_name: str, args: dict) -> bool:
            return True
            
    return PermissionPolicy(
        name="yolo",
        rules=[AnyRule(tool="any", decision=PermissionDecision.ALLOW)]
    )
