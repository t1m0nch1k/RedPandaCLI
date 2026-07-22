from __future__ import annotations

import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Role
    content: str
    images: list[str] | None = None
    created_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[Message] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None

    def add(self, role: Role, content: str, images: list[str] | None = None, **metadata: Any) -> Message:
        msg = Message(role=role, content=content, images=images, metadata=metadata)
        self.messages.append(msg)
        return msg


class ToolResult(BaseModel):
    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    data: dict[str, Any] = Field(default_factory=dict)
    image_b64: str | None = None


class StreamChunk(BaseModel):
    type: str  # "content" | "tool_call" | "done"
    content: str = ""
    tool_calls: list[dict] | None = None
