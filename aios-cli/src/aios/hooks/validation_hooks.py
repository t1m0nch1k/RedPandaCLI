from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aios.core.models import Role
from aios.hooks.events import HookAction, HookContext

logger = logging.getLogger(__name__)

MODIFYING_TOOLS = {
    "write", "edit", "delete", "multi_edit", "rename_symbol",
    "move_file", "apply_patch", "write_to_file", "patch", "replace_text",
}

def make_test_validation_hook(workspace_root: Path, max_retries: int = 3):
    """
    Creates a hook that automatically runs tests when files are modified.
    If tests fail, the error is injected back into the conversation to trigger a self-correction loop.
    """
    retry_count = 0

    async def hook(ctx: HookContext) -> HookAction:
        nonlocal retry_count
        
        # Only run on POST_TOOL events for modifying tools that succeeded
        if not ctx.tool_name or ctx.tool_name not in MODIFYING_TOOLS:
            return HookAction.CONTINUE
            
        if not ctx.tool_result or not ctx.tool_result.success:
            return HookAction.CONTINUE
            
        # Check if tests exist
        tests_dir = workspace_root / "tests"
        if not tests_dir.exists():
            return HookAction.CONTINUE
            
        logger.info(f"Running automated validation tests after {ctx.tool_name}...")
        
        try:
            # We assume pytest for python projects. 
            # A more generic implementation could check aios.config for test command.
            process = await asyncio.create_subprocess_exec(
                "pytest",
                cwd=str(workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                retry_count += 1
                if retry_count <= max_retries:
                    output = stdout.decode('utf-8', errors='ignore')[-3000:]  # Limit output size
                    error_msg = f"[Validation Hook] Automated tests failed after your changes (Attempt {retry_count}/{max_retries}). Please fix the following errors:\n\n{output}"
                    
                    logger.warning(f"Tests failed. Injecting feedback into conversation (Retry {retry_count}/{max_retries}).")
                    ctx.conversation.add(Role.SYSTEM, error_msg)
                else:
                    logger.error(f"Max retries ({max_retries}) reached for test failures. Giving up.")
                    ctx.conversation.add(Role.SYSTEM, f"[Validation Hook] Tests continue to fail after {max_retries} attempts. Proceed manually.")
                    retry_count = 0  # Reset for next manual attempt
            else:
                if retry_count > 0:
                    logger.info("Tests passed! Self-correction successful.")
                    ctx.conversation.add(Role.SYSTEM, "[Validation Hook] Tests passed! Your changes fixed the issue.")
                retry_count = 0
                
        except FileNotFoundError:
            logger.debug("pytest not found, skipping validation.")
        except Exception as e:
            logger.error(f"Validation hook failed: {e}")

        return HookAction.CONTINUE

    return hook
