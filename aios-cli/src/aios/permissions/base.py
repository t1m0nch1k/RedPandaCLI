from __future__ import annotations

from enum import Enum, auto


class PermissionDecision(Enum):
    """
    The outcome of a permission check.
    """
    ALLOW = auto()          # Execute without asking
    DENY = auto()           # Block execution
    ASK = auto()            # Ask the user for confirmation
    ALWAYS_ALLOW = auto()   # Execute and remember this decision for future identical calls
