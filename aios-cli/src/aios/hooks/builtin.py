from __future__ import annotations

from aios.hooks.events import HookAction, HookContext, HookEvent


async def auto_commit_hook(context: HookContext) -> HookAction:
    """
    Example hook: Suggests or performs an auto-commit after a successful filesystem write.
    """
    if context.event == HookEvent.POST_TOOL:
        tool_name = context.tool_name
        if tool_name == "filesystem" and context.tool_result and context.tool_result.success:
            # In a real implementation, this would check if files were actually changed
            # and then call the git tool to commit.
            # For now, we just log it.
            print(f"Hook: Detected change via {tool_name}. Consider committing.")
            
    return HookAction.CONTINUE

async def cost_tracker_hook(context: HookContext) -> HookAction:
    """
    Example hook: Tracks token usage after each response.
    """
    if context.event == HookEvent.POST_RESPONSE:
        # Logic to extract usage from context.response and add to a tracker
        pass
        
    return HookAction.CONTINUE
