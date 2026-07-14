from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class HookEvent(Enum):
    """
    Lifecycle events where hooks can be triggered.
    """
    PRE_TOOL = auto()     # Before a tool is executed
    POST_TOOL = auto()    # After a tool is executed
    PRE_PROMPT = auto()   # Before the LLM is called
    POST_RESPONSE = auto() # After the LLM responds
    SESSION_START = auto() # When a session begins
    SESSION_END = auto()   # When a session ends
    ERROR = auto()        # When an unexpected error occurs

@dataclass
class HookContext:
    """
    Context passed to hooks, containing all relevant data for the event.
    """
    event: HookEvent
    conversation: Any # Conversation object
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: Any | None = None
    response: Any | None = None
    error: Exception | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class HookAction(Enum):
    """
    The action requested by a hook.
    """
    CONTINUE = auto()    # Proceed as normal
    BLOCK = auto()       # Block the current operation
    MODIFY = auto()      # The hook modified the context/conversation (not fully implemented yet)
