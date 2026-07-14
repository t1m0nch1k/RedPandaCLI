from __future__ import annotations

from typing import Any

from aios.config.settings import GitConfig
from aios.core.models import Conversation
from aios.executor.engine import ExecutionEngine
from aios.permissions.manager import PermissionManager
from aios.permissions.profiles import get_trusted_policy
from aios.providers.base import LLMProvider
from aios.tools.registry import ToolRegistry


class Agent:
    def __init__(
        self, 
        provider: LLMProvider, 
        tool_registry: ToolRegistry, 
        mcp_servers: list[dict[str, Any]] | None = None, 
        git_config: GitConfig | None = None,
        state_callback=None
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        
        # Initialize permissions with the trusted profile by default
        self.permission_manager = PermissionManager(policy=get_trusted_policy())
        
        self.engine = ExecutionEngine(
            provider=self.provider,
            tool_registry=self.tool_registry,
            permission_manager=self.permission_manager,
            mcp_servers=mcp_servers or [],
            git_config=git_config,
            state_callback=state_callback,
        )

    async def run(self, conversation: Conversation, max_iterations: int = 10, stream_callback=None) -> str:
        return await self.engine.run(conversation, max_iterations, stream_callback=stream_callback)
