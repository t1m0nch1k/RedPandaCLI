from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aios.config.settings import GitConfig
from aios.core.models import Conversation
from aios.executor.agent import Agent
from aios.executor.engine import ExecutionEngine
from aios.providers.base import LLMProvider
from aios.runtime.models import ExecutionState
from aios.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Type for the confirmation callback: (tool_name, args) -> bool
ConfirmationCallback = Callable[[str, dict[str, Any]], Awaitable[bool]]
# Type for the state callback: (state: ExecutionState) -> None
StateCallback = Callable[[ExecutionState], None]

CODING_SYSTEM_PROMPT = """\
You are an expert AI Software Engineer. Help the user develop, refactor, and debug code with surgical precision.

### OPERATIONAL GUIDELINES:
1. **Explore First**: Before changes, use the `filesystem` tool with `action="list_files"` and `action="read_file"`
   to understand the project structure and existing implementation.
2. **Create & Edit Files**: NEVER output raw code blocks as your final answer if you were asked to write code! 
   ALWAYS use the `filesystem` tool with `action="create_file"` to create new files, or `action="replace_text"` to modify existing ones.
   For edits, provide the EXACT existing text to be replaced. Do not rewrite entire files.
3. **Verify Changes**: After modifying code, use `shell` to run tests, linters, or
   the application to verify that your changes work and didn't introduce regressions.
4. **Context Management**: Read only the necessary parts of the file using `action="read_file_range"` if the file is large.
5. **Iterative Process**: If a tool call fails or a test fails, analyze the error and try a different approach.

### TOOL USAGE TIPS:
- The `filesystem` tool is your primary way to interact with code. Set the `action` parameter to what you need (`create_file`, `replace_text`, `search_text`, etc).
- Use `action="search_text"` with regex to find symbols or patterns across the project.
- Use `git` to check the current status or create commits after a successful task.

CRITICAL INSTRUCTION: You MUST use the provided tools to accomplish the user's request. Do NOT simply state what you plan to do, and DO NOT output raw code blocks instead of creating files. Actively call the tools immediately in your response to gather context and make changes autonomously. Do not ask for permission to use tools.

Your final response should be a concise summary of what you did and the current state.
"""

class CodingAgent(Agent):
    def __init__(
        self, 
        provider: LLMProvider, 
        tool_registry: ToolRegistry, 
        confirmation_callback: ConfirmationCallback | None = None,
        state_callback: StateCallback | None = None,
        mcp_servers: list[dict[str, Any]] | None = None,
        git_config: GitConfig | None = None,
    ) -> None:
        super().__init__(provider, tool_registry, mcp_servers=mcp_servers, git_config=git_config)
        
        # Initialize a dedicated PermissionManager for the coding agent
        from aios.permissions.manager import PermissionManager
        from aios.permissions.profiles import get_trusted_policy
        self.permission_manager = PermissionManager(policy=get_trusted_policy())
        
        # Overwrite the engine with a specialized configuration for coding
        self.engine = ExecutionEngine(
            provider=self.provider,
            tool_registry=self.tool_registry,
            permission_manager=self.permission_manager,
            confirmation_callback=confirmation_callback,
            state_callback=state_callback,
            system_prompt=CODING_SYSTEM_PROMPT,
            mcp_servers=mcp_servers or [],
            git_config=git_config,
        )

    async def run(self, conversation: Conversation, max_iterations: int = 15, stream_callback=None) -> str:
        return await self.engine.run(conversation, max_iterations, stream_callback=stream_callback)
