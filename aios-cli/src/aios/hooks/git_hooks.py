from __future__ import annotations

import logging
from pathlib import Path

from aios.config.settings import GitConfig
from aios.hooks.events import HookAction, HookContext
from aios.tools.git import PROTECTED_BRANCHES, _check_secrets, _run_git

logger = logging.getLogger(__name__)

FILESYSTEM_TOOLS = {
    "filesystem", "read", "write", "edit", "delete",
    "glob", "grep", "multi_edit", "rename_symbol",
    "move_file", "preview_diff", "apply_patch",
}


def make_auto_commit_hook(git_config: GitConfig, workspace_root: Path):
    async def hook(ctx: HookContext) -> HookAction:
        if not git_config.auto_commit:
            return HookAction.CONTINUE
        if not ctx.tool_name or ctx.tool_name not in FILESYSTEM_TOOLS:
            return HookAction.CONTINUE
        if not ctx.tool_result or not ctx.tool_result.success:
            return HookAction.CONTINUE

        cwd = str(workspace_root)

        try:
            diff_out, _, diff_code = await _run_git(["diff", "--cwd", cwd], cwd)
            if diff_code != 0:
                return HookAction.CONTINUE
            if not diff_out.strip():
                return HookAction.CONTINUE

            branch_out, _, _ = await _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
            current_branch = branch_out.strip()
            if current_branch in (git_config.protected_branches or PROTECTED_BRANCHES):
                return HookAction.CONTINUE

            if git_config.secret_scanning:
                secrets = _check_secrets(diff_out)
                if secrets:
                    logger.warning("Secrets detected in auto-commit diff; skipping auto-commit")
                    return HookAction.CONTINUE

            await _run_git(["add", "-A"], cwd)
            message = f"{git_config.commit_prefix}auto: {ctx.tool_name} changes"
            _, _, commit_code = await _run_git(["commit", "-m", message], cwd)
            if commit_code == 0:
                logger.info("Auto-commit: %s", message)
        except Exception as e:
            logger.warning("Auto-commit hook failed: %s", e)

        return HookAction.CONTINUE

    return hook
