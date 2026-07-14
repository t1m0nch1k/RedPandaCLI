from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from aios.runtime.models import ExecutionState
from aios.config.settings import GitConfig
from aios.context.manager import ContextManager
from aios.core.models import Conversation, Role, StreamChunk, ToolResult
from aios.hooks.events import HookAction, HookContext, HookEvent
from aios.hooks.git_hooks import make_auto_commit_hook
from aios.hooks.manager import HookManager
from aios.mcp.registry import MCPRegistry
from aios.memory.auto import AutoMemory
from aios.memory.project import ProjectMemory
from aios.permissions.base import PermissionDecision
from aios.permissions.manager import PermissionManager
from aios.plugins.registry import PluginRegistry
from aios.providers.base import LLMProvider
from aios.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Type for the confirmation callback: (tool_name, args) -> bool
ConfirmationCallback = Callable[[str, dict[str, Any]], Awaitable[bool]]
# Type for the state callback: (state: ExecutionState) -> None
StateCallback = Callable[[ExecutionState], None]
# Type for the stream callback: (chunk: StreamChunk) -> None
StreamCallback = Callable[[StreamChunk], Awaitable[None] | None]

class ExecutionEngine:
    """
    The core engine responsible for orchestrating the agent loop:
    LLM request -> Tool Execution -> Response -> Loop.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        permission_manager: PermissionManager,
        hook_manager: HookManager | None = None,
        confirmation_callback: ConfirmationCallback | None = None,
        state_callback: StateCallback | None = None,
        system_prompt: str | None = None,
        workspace_root: Path | None = None,
        mcp_servers: list[dict[str, Any]] | None = None,
        git_config: GitConfig | None = None,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager
        self.hook_manager = hook_manager or HookManager()
        self.confirmation_callback = confirmation_callback
        self.state_callback = state_callback
        self.system_prompt = system_prompt
        self.workspace_root = workspace_root or Path.cwd()
        self.git_config = git_config or GitConfig()
        
        # Memory systems
        self.project_memory = ProjectMemory(self.workspace_root)
        self.auto_memory = AutoMemory(self.workspace_root)
        
        # Context management
        self.context_manager = ContextManager(model_name=provider.model)

        # MCP
        self.mcp_registry = MCPRegistry()
        self.mcp_registry.configure(mcp_servers or [])

        # Plugin system
        self.plugin_registry = PluginRegistry(
            tool_registry=self.tool_registry,
            hook_manager=self.hook_manager,
        )

    def _get_tool_definitions(self) -> list[dict]:
        tools = []
        for tool in self.tool_registry.list():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters or {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            })
        return tools

    def _update_state(self, state: ExecutionState) -> None:
        if self.state_callback:
            self.state_callback(state)

    async def run(self, conversation: Conversation, max_iterations: int, stream_callback: StreamCallback | None = None) -> str:
        # Register auto-commit hook if enabled
        if self.git_config.auto_commit:
            self.hook_manager.register(
                HookEvent.POST_TOOL,
                make_auto_commit_hook(self.git_config, self.workspace_root),
            )
            
        # Register automated validation hook
        # Ideally, we get TestConfig here, but we can just use get_settings()
        from aios.config.settings import get_settings
        from aios.hooks.validation_hooks import make_test_validation_hook
        test_config = get_settings().testing
        if test_config.auto_test:
            self.hook_manager.register(
                HookEvent.POST_TOOL,
                make_test_validation_hook(self.workspace_root),
            )

        # Load plugins
        await self.plugin_registry.load_all()

        # Session Start Hook
        await self.hook_manager.trigger(
            HookEvent.SESSION_START, 
            HookContext(event=HookEvent.SESSION_START, conversation=conversation)
        )

        # Connect MCP servers and register their tools
        mcp_tools = await self.mcp_registry.connect_all()
        for tool in mcp_tools:
            self.tool_registry.register(tool)
        if mcp_tools:
            logger.info(f"MCP: {len(mcp_tools)} tool(s) from {len(self.mcp_registry.connected_servers)} server(s)")

        # Load and inject project memory (AIOS.md and AutoMemory)
        project_context = self.project_memory.load_context()
        auto_context = self.auto_memory.recall()
        
        if project_context or auto_context:
            memory_prompt = f"{project_context}\n\n{auto_context}".strip()
            if not any(msg.role == Role.SYSTEM and memory_prompt in msg.content for msg in conversation.messages):
                from aios.core.models import Message
                conversation.messages.insert(0, Message(role=Role.SYSTEM, content=memory_prompt))

        # Inject system prompt and workspace info
        sys_info = f"[System Info]\nCurrent Workspace Root: {self.workspace_root.absolute()}"
        
        # Inject Active Plan if it exists to focus the LLM
        plan_path = self.workspace_root / ".aios" / "plan.md"
        if plan_path.exists():
            plan_content = plan_path.read_text(encoding="utf-8", errors="ignore")
            sys_info += (
                f"\n\n[Active Plan]\n{plan_content}\n\n"
                "INSTRUCTIONS: You are executing a plan. Focus ONLY on completing the first unchecked task ([ ]). "
                "Do not try to do everything at once. Once you complete the task, use `task_manager` to mark it `done`."
            )
        else:
            sys_info += (
                "\n\nINSTRUCTIONS: If the user request is complex and requires multiple steps, "
                "use the `task_manager` tool to create a detailed plan in `.aios/plan.md` "
                "before taking any other actions."
            )
            
        full_system_prompt = f"{self.system_prompt}\n\n{sys_info}" if self.system_prompt else sys_info
        
        if not any(msg.role == Role.SYSTEM and "[System Info]" in msg.content for msg in conversation.messages):
            from aios.core.models import Message
            conversation.messages.insert(0, Message(role=Role.SYSTEM, content=full_system_prompt))

        tool_defs = self._get_tool_definitions()
        
        force_sweep_next = False
        
        for i in range(max_iterations):
            # Manage context budget and apply compaction if necessary
            await self.context_manager.manage(conversation, self.provider, force_sweep=force_sweep_next)
            force_sweep_next = False
            
            self._update_state(ExecutionState.THINKING)
            logger.info(f"Iteration {i + 1}/{max_iterations}. Sending request to {self.provider.name} model {self.provider.model}")
            
            # Pre-prompt Hook
            if await self.hook_manager.trigger(
                HookEvent.PRE_PROMPT, 
                HookContext(event=HookEvent.PRE_PROMPT, conversation=conversation)
            ) == HookAction.BLOCK:
                return "Execution blocked by pre-prompt hook."

            content: str | None = None
            tool_calls: list[dict] | None = None

            if stream_callback:
                full_content = ""
                async for chunk in self.provider.stream_chat(
                    conversation.messages, tools=tool_defs
                ):
                    if chunk.type == "content":
                        full_content += chunk.content
                        await stream_callback(chunk)
                    elif chunk.type == "tool_call":
                        tool_calls = chunk.tool_calls
                content = full_content if full_content else None
            else:
                response = await self.provider.chat(
                    conversation.messages, 
                    tools=tool_defs
                )
                # Post-response Hook
                await self.hook_manager.trigger(
                    HookEvent.POST_RESPONSE, 
                    HookContext(event=HookEvent.POST_RESPONSE, conversation=conversation, response=response)
                )
                content = response.get("content")
                tool_calls = response.get("tool_calls")
                if content:
                    logger.info(f"Assistant replied with {len(content)} chars of text.")
            
            if tool_calls:
                logger.info(f"Assistant invoked {len(tool_calls)} tool(s).")

            # Always add the assistant message, even if empty, so the UI can save it with a unique ID
            # and to maintain proper chat history sequence.
            conversation.add(Role.ASSISTANT, content or "", tool_calls=tool_calls)
            
            if not tool_calls:
                self._update_state(ExecutionState.DONE)
                final = content or "I've completed the task or I'm stuck. Please provide more guidance."
                await self._cleanup(conversation)
                return final

            # Execute Tools
            for tool_call in tool_calls:
                self._update_state(ExecutionState.TOOL)
                
                func_name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]
                result: ToolResult | None = None
                
                logger.info(f"Executing tool: {func_name} with args: {args}")
                
                # Handle string arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        result = ToolResult(success=False, error=f"Invalid JSON arguments: {args}")
                
                if isinstance(args, dict):
                    # Pre-tool Hook
                    if await self.hook_manager.trigger(
                        HookEvent.PRE_TOOL, 
                        HookContext(event=HookEvent.PRE_TOOL, conversation=conversation, tool_name=func_name, tool_args=args)
                    ) == HookAction.BLOCK:
                        result = ToolResult(success=False, error="Action blocked by pre-tool hook.")
                    
                    if result is None:
                        # Permission Check
                        decision = self.permission_manager.check(func_name, args)
                        
                        if decision == PermissionDecision.DENY:
                            result = ToolResult(success=False, error="Action denied by permission policy.")
                        elif decision == PermissionDecision.ASK:
                            if self.confirmation_callback:
                                confirmed = await self.confirmation_callback(func_name, args)
                                if not confirmed:
                                    result = ToolResult(success=False, error="User declined the action.")
                            else:
                                result = ToolResult(success=False, error="Action requires user confirmation, but no confirmation handler is configured.")
                        
                        # Execution
                        if result is None:
                            tool = self.tool_registry.get(func_name)
                            if tool:
                                result = await tool.run_timed(**args)
                            else:
                                result = ToolResult(success=False, error=f"Tool {func_name} not found")
                elif result is None:
                    result = ToolResult(
                        success=False,
                        error=f"Invalid arguments for {func_name}: expected object",
                    )

                # Truncate large tool results before adding to conversation
                if result and result.success and result.output:
                    truncated_output, _ = self.context_manager.compactor.truncate_tool_result(result.output)
                    result.output = truncated_output

                # Post-tool Hook
                await self.hook_manager.trigger(
                    HookEvent.POST_TOOL, 
                    HookContext(event=HookEvent.POST_TOOL, conversation=conversation, tool_name=func_name, tool_args=args, tool_result=result)
                )

                if not result.success:
                    self._update_state(ExecutionState.ERROR)

                # Add tool result to conversation
                output_text = f"Tool {func_name} result: {result.output if result.success else result.error}"
                conversation.add(
                    Role.TOOL, 
                    output_text, 
                    tool_call_id=tool_call.get("id"),
                    name=func_name
                )
                logger.info(f"Tool {func_name} completed with success={result.success}")
                
                if func_name == "context_sweep":
                    force_sweep_next = True
        
        await self._cleanup(conversation)
        return "Maximum iterations reached without a final answer."

    async def _cleanup(self, conversation: Conversation) -> None:
        await self.hook_manager.trigger(
            HookEvent.SESSION_END,
            HookContext(event=HookEvent.SESSION_END, conversation=conversation),
        )
        await self.mcp_registry.disconnect_all()
        for plugin in self.plugin_registry.list_plugins():
            if plugin.enabled:
                try:
                    await plugin.on_unload()
                except Exception:
                    pass
