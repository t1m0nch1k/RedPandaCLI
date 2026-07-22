from __future__ import annotations

import json
import platform
from dataclasses import asdict
from datetime import datetime
from typing import Any

from aios.core.models import Message
from aios.memory.orchestrator import MemoryOrchestrator
from aios.runtime.prompt_assembler.base import PromptAssemblerProtocol


class DefaultPromptAssembler(PromptAssemblerProtocol):
    """
    Standard prompt assembler that aggregates:
    - Base system prompt
    - Memory/Project context
    - OS/Environment info
    - Tools and their definitions
    - Conversation history
    """
    def __init__(self, memory_orchestrator: MemoryOrchestrator | None = None) -> None:
        self.memory = memory_orchestrator

    async def assemble(
        self,
        conversation: Any,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        memory_context: str = "",
    ) -> list[Message]:
        messages = []
        
        # 1. Build Base System Prompt
        sys_parts = []
        if system_prompt:
            sys_parts.append(system_prompt)
            
        # 2. Inject OS Context
        sys_info = (
            f"[System Environment]\n"
            f"OS: {platform.system()} {platform.release()}\n"
            f"Time: {datetime.now().isoformat()}"
        )
        sys_parts.append(sys_info)

        # 3. Inject Memory Context
        if self.memory:
            orchestrator_context = self.memory.get_active_context()
            if orchestrator_context:
                sys_parts.append(orchestrator_context)
                
        if memory_context:
            sys_parts.append(memory_context)

        # Combine system prompt
        final_system_prompt = "\n\n".join(sys_parts)
        if final_system_prompt:
            # We assume the Conversation or Message classes handle formatting.
            # In aios, the provider expects standard Message objects.
            messages.append(Message(role="system", content=final_system_prompt))

        # 4. Add Conversation History
        # We assume `conversation` is a list of Messages or an object that can provide them.
        if isinstance(conversation, list):
            messages.extend(conversation)
        elif hasattr(conversation, "messages"):
            messages.extend(conversation.messages)
            
        return messages

    async def assemble_with_plan(
        self,
        conversation: Any,
        plan: Any,
        current_step: Any | None = None,
    ) -> list[Message]:
        """
        Builds the prompt injecting the current execution plan and step.
        """
        # First assemble standard prompt
        messages = await self.assemble(conversation)
        
        # Extract system message to append plan
        sys_idx = -1
        for i, msg in enumerate(messages):
            if msg.role == "system":
                sys_idx = i
                break
                
        plan_context = f"\n\n[Active Plan]\n{json.dumps(asdict(plan), indent=2, default=str)}\n"
        if current_step:
            plan_context += f"\n[Current Step]\n{json.dumps(asdict(current_step), indent=2, default=str)}\n"
            
        if sys_idx >= 0:
            messages[sys_idx].content += plan_context
        else:
            messages.insert(0, Message(role="system", content=plan_context))
            
        return messages
