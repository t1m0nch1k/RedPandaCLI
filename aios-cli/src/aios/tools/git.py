from __future__ import annotations

import re
from typing import Any

from aios.config.settings import GitConfig
from aios.core.models import ToolResult
from aios.tools.base import Tool
from aios.workspace import WorkspaceContext

SECRET_PATTERNS = [
    r"(?i)(?:api[_-]?key|secret|token|password|passwd|pwd|credential)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{16,}",
    r"(?i)-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
    r"(?i)ghp_[A-Za-z0-9]{36,}",
    r"(?i)sk-[A-Za-z0-9\-_]{20,}",
    r"(?i)AKIA[0-9A-Z]{16}",
]

PROTECTED_BRANCHES = ["main", "master", "develop"]


async def _run_git(args: list[str], cwd: str) -> tuple[str, str, int]:
    import asyncio
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"), proc.returncode or 0


def _check_secrets(content: str) -> list[str]:
    found = []
    for pattern in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        for m in matches:
            found.append(m[:40])
    return found


class GitTool(Tool):
    name = "git"
    description = "Semantic git operations: status, diff, commit, branch, log, stash, worktree, push, pull"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "status", "diff", "commit", "log", "branch",
                    "stash", "worktree", "add", "push", "pull",
                    "init", "clone", "smart_commit",
                ],
                "description": "The git action to perform",
            },
            "message": {"type": "string", "description": "Commit message"},
            "branch": {"type": "string", "description": "Branch name for branch/worktree actions"},
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths for add/commit",
            },
            "stash_action": {
                "type": "string",
                "enum": ["push", "pop", "list", "drop"],
                "description": "Stash sub-action",
            },
            "worktree_action": {
                "type": "string",
                "enum": ["add", "list", "remove"],
                "description": "Worktree sub-action",
            },
            "branch_action": {
                "type": "string",
                "enum": ["list", "create", "delete", "switch", "merge"],
                "description": "Branch sub-action",
            },
            "count": {"type": "integer", "description": "Number of log entries (default: 10)"},
            "force": {"type": "boolean", "description": "Allow force push (requires confirmation)"},
            "remote": {"type": "string", "description": "Remote name (default: origin)"},
            "url": {"type": "string", "description": "Remote URL for clone/push"},
        },
        "required": ["action"],
    }

    def __init__(self, workspace: WorkspaceContext | None = None, git_config: GitConfig | None = None) -> None:
        self.workspace = workspace or WorkspaceContext.from_cwd()
        self._git_config = git_config or GitConfig()

    def _cwd(self) -> str:
        return str(self.workspace.root)

    async def run(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "")
        handler = {
            "status": self._status,
            "diff": self._diff,
            "commit": self._commit,
            "smart_commit": self._smart_commit,
            "log": self._log,
            "branch": self._branch,
            "stash": self._stash,
            "worktree": self._worktree,
            "add": self._add,
            "push": self._push,
            "pull": self._pull,
            "init": self._init,
            "clone": self._clone,
        }.get(action)
        if not handler:
            return ToolResult(success=False, error=f"Unknown git action: {action}")
        return await handler(kwargs)

    async def _status(self, _: dict[str, Any]) -> ToolResult:
        out, err, code = await _run_git(["--no-pager", "status", "--short", "--branch"], self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git status failed")
        long_out, _, _ = await _run_git(["--no-pager", "status"], self._cwd())

        staged = []
        unstaged = []
        untracked = []
        for line in out.splitlines():
            line = line.rstrip()
            if len(line) < 3:
                continue
            x = line[0]
            y = line[1]
            path = line[3:].strip()
            if x != " " and y == " ":
                staged.append(f"{x} {path}")
            elif x == " " and y != " " and y != "?":
                unstaged.append(f"{y} {path}")
            elif x != " " and y != " ":
                staged.append(f"{x} {path}")
                if y != "?":
                    unstaged.append(f"{y} {path}")
            if x == "?" or y == "?":
                untracked.append(f"? {path}")

        branch_info = ""
        for line in long_out.splitlines():
            if line.startswith("On branch") or line.startswith("HEAD detached"):
                branch_info = line
                break

        result = [f"## {branch_info}"] if branch_info else []
        if staged:
            result.append(f"\nStaged ({len(staged)}):\n" + "\n".join(staged))
        if unstaged:
            result.append(f"\nUnstaged ({len(unstaged)}):\n" + "\n".join(unstaged))
        if untracked:
            result.append(f"\nUntracked ({len(untracked)}):\n" + "\n".join(untracked))

        return ToolResult(success=True, output="\n".join(result) or "Clean working tree")

    async def _diff(self, kwargs: dict[str, Any]) -> ToolResult:
        args = ["--no-pager", "diff"]
        if kwargs.get("staged"):
            args.append("--staged")
        out, err, code = await _run_git(args, self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git diff failed")
        if not out.strip():
            return ToolResult(success=True, output="No differences")
        return ToolResult(success=True, output=out)

    async def _commit(self, kwargs: dict[str, Any]) -> ToolResult:
        message = kwargs.get("message", "")
        if not message:
            return ToolResult(success=False, error="Commit message is required for 'commit' action. Use 'smart_commit' for auto-generation.")

        paths = kwargs.get("paths", [])
        if paths:
            add_out, add_err, add_code = await _run_git(["add", "--"] + paths, self._cwd())
            if add_code != 0:
                return ToolResult(success=False, error=f"git add failed: {add_err}")

        branch_out, _, _ = await _run_git(["rev-parse", "--abbrev-ref", "HEAD"], self._cwd())
        current_branch = branch_out.strip()
        protected = self._git_config.protected_branches
        if current_branch in protected:
            return ToolResult(success=False, error=f"Cannot commit directly to protected branch '{current_branch}'. Switch branches first.")

        diff_check, _, _ = await _run_git(["diff", "--cached"], self._cwd())
        if not diff_check.strip():
            return ToolResult(success=False, error="Nothing to commit. Use paths or 'git add' first.")

        if self._git_config.secret_scanning:
            secrets = _check_secrets(diff_check)
        else:
            secrets = []
        if secrets:
            secrets_str = "\n".join(f"  - {s}" for s in secrets[:5])
            return ToolResult(success=False, error=f"Potential secrets detected in staged changes:\n{secrets_str}\n\nRemove them before committing.")

        out, err, code = await _run_git(["commit", "-m", message], self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git commit failed")
        return ToolResult(success=True, output=out.strip())

    async def _smart_commit(self, kwargs: dict[str, Any]) -> ToolResult:
        diff_out, _, _ = await _run_git(["diff"], self._cwd())
        staged_diff, _, _ = await _run_git(["diff", "--cached"], self._cwd())
        status_out, _, _ = await _run_git(["--no-pager", "status", "--porcelain"], self._cwd())

        has_changes = bool(diff_out.strip() or staged_diff.strip() or status_out.strip())
        if not has_changes:
            return ToolResult(success=False, error="Nothing to commit. No changes detected.")

        message = kwargs.get("message", "")
        if not message:
            files_changed = set()
            for line in diff_out.splitlines():
                if line.startswith("diff --git"):
                    parts = line.split()
                    if len(parts) >= 3:
                        f = parts[2].replace("a/", "", 1)
                        files_changed.add(f)
            for line in status_out.splitlines():
                line = line.rstrip()
                if len(line) >= 3 and line[:2].strip() == "?":
                    files_changed.add(line[3:].strip())
            summary = ", ".join(sorted(files_changed)[:10])
            message = f"Update {summary}" if summary else "Update"
            if len(files_changed) > 10:
                message += f" and {len(files_changed) - 10} more"

        await _run_git(["add", "-A"], self._cwd())
        return await self._commit({"message": message, "paths": []})

    async def _log(self, kwargs: dict[str, Any]) -> ToolResult:
        count = min(kwargs.get("count", 10), 100)
        out, err, code = await _run_git(
            ["--no-pager", "log", f"-{count}", "--format=%h|%an|%ar|%s", "--no-color"],
            self._cwd(),
        )
        if code != 0 and "does not have any commits yet" in err:
            return ToolResult(success=True, output="No commits yet")
        if code != 0:
            return ToolResult(success=False, error=err or "git log failed")

        entries = []
        for line in out.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                entries.append(f"  {parts[0]}  {parts[1]}  {parts[2]}  {parts[3]}")

        if not entries:
            return ToolResult(success=True, output="No commits yet")

        return ToolResult(success=True, output="Recent commits:\n" + "\n".join(entries))

    async def _branch(self, kwargs: dict[str, Any]) -> ToolResult:
        sub = kwargs.get("branch_action", "list")
        branch = kwargs.get("branch", "")

        if sub == "list":
            out, err, code = await _run_git(["branch", "--no-color"], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or "git branch failed")
            return ToolResult(success=True, output=out.strip())

        if sub == "create":
            if not branch:
                return ToolResult(success=False, error="Branch name required")
            out, err, code = await _run_git(["branch", branch], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or f"Failed to create branch '{branch}'")
            return ToolResult(success=True, output=f"Created branch '{branch}'")

        if sub == "delete":
            if not branch:
                return ToolResult(success=False, error="Branch name required")
            if branch in self._git_config.protected_branches:
                return ToolResult(success=False, error=f"Cannot delete protected branch '{branch}'")
            out, err, code = await _run_git(["branch", "-D", branch], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or f"Failed to delete branch '{branch}'")
            return ToolResult(success=True, output=f"Deleted branch '{branch}'")

        if sub == "switch":
            if not branch:
                return ToolResult(success=False, error="Branch name required")
            out, err, code = await _run_git(["checkout", branch], self._cwd())
            if code != 0:
                create = kwargs.get("create", False)
                if create:
                    out, err, code = await _run_git(["checkout", "-b", branch], self._cwd())
                    if code != 0:
                        return ToolResult(success=False, error=err or f"Failed to switch to '{branch}'")
                    return ToolResult(success=True, output=f"Created and switched to '{branch}'")
                return ToolResult(success=False, error=err or f"Failed to switch to '{branch}'")
            return ToolResult(success=True, output=f"Switched to '{branch}'")

        return ToolResult(success=False, error=f"Unknown branch action: {sub}")

    async def _stash(self, kwargs: dict[str, Any]) -> ToolResult:
        sub = kwargs.get("stash_action", "push")
        message = kwargs.get("message", "")

        if sub == "push":
            args = ["stash", "push", "--include-untracked"]
            if message:
                args.extend(["-m", message])
            out, err, code = await _run_git(args, self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or "git stash failed")
            return ToolResult(success=True, output=out.strip() or "Stashed changes")

        if sub == "pop":
            out, err, code = await _run_git(["stash", "pop"], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or "Nothing to pop")
            return ToolResult(success=True, output=out.strip() or "Popped stash")

        if sub == "list":
            out, err, code = await _run_git(["stash", "list"], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or "git stash list failed")
            return ToolResult(success=True, output=out.strip() or "No stashes")

        if sub == "drop":
            out, err, code = await _run_git(["stash", "drop"], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or "Nothing to drop")
            return ToolResult(success=True, output="Dropped latest stash")

        return ToolResult(success=False, error=f"Unknown stash action: {sub}")

    async def _worktree(self, kwargs: dict[str, Any]) -> ToolResult:
        sub = kwargs.get("worktree_action", "list")
        path = kwargs.get("path", "")
        branch = kwargs.get("branch", "")

        if sub == "list":
            out, err, code = await _run_git(["worktree", "list"], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or "git worktree list failed")
            return ToolResult(success=True, output=out.strip())

        if sub == "add":
            if not path or not branch:
                return ToolResult(success=False, error="Both 'path' and 'branch' are required for worktree add")
            out, err, code = await _run_git(["worktree", "add", path, branch], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or f"Failed to add worktree '{path}'")
            return ToolResult(success=True, output=f"Added worktree '{path}' for branch '{branch}'")

        if sub == "remove":
            if not path:
                return ToolResult(success=False, error="'path' is required for worktree remove")
            out, err, code = await _run_git(["worktree", "remove", path], self._cwd())
            if code != 0:
                return ToolResult(success=False, error=err or f"Failed to remove worktree '{path}'")
            return ToolResult(success=True, output=f"Removed worktree '{path}'")

        return ToolResult(success=False, error=f"Unknown worktree action: {sub}")

    async def _add(self, kwargs: dict[str, Any]) -> ToolResult:
        paths = kwargs.get("paths", [])
        if not paths:
            return ToolResult(success=False, error="'paths' is required for add (use ['*'] for all)")
        out, err, code = await _run_git(["add", "--"] + paths, self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git add failed")
        return ToolResult(success=True, output=f"Staged {len(paths)} path(s)")

    async def _push(self, kwargs: dict[str, Any]) -> ToolResult:
        remote = kwargs.get("remote", "origin")
        branch = kwargs.get("branch", "")
        force = kwargs.get("force", False)

        if force:
            branch_out, _, _ = await _run_git(["rev-parse", "--abbrev-ref", "HEAD"], self._cwd())
            current = branch_out.strip()
            if current in self._git_config.protected_branches:
                return ToolResult(success=False, error=f"Force push to protected branch '{current}' is blocked. Create a feature branch instead.")

        args = ["push", remote]
        if branch:
            args.append(branch)
        if force:
            args.append("--force")

        out, err, code = await _run_git(args, self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git push failed")
        return ToolResult(success=True, output=out.strip() or f"Pushed to {remote}")

    async def _pull(self, kwargs: dict[str, Any]) -> ToolResult:
        remote = kwargs.get("remote", "origin")
        branch = kwargs.get("branch", "")
        args = ["pull", remote]
        if branch:
            args.append(branch)
        out, err, code = await _run_git(args, self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git pull failed")
        return ToolResult(success=True, output=out.strip() or f"Pulled from {remote}")

    async def _init(self, _: dict[str, Any]) -> ToolResult:
        out, err, code = await _run_git(["init"], self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git init failed")
        return ToolResult(success=True, output=out.strip() or "Initialized empty git repo")

    async def _clone(self, kwargs: dict[str, Any]) -> ToolResult:
        url = kwargs.get("url", "")
        if not url:
            return ToolResult(success=False, error="'url' is required for clone")
        out, err, code = await _run_git(["clone", url], self._cwd())
        if code != 0:
            return ToolResult(success=False, error=err or "git clone failed")
        return ToolResult(success=True, output=out.strip() or f"Cloned {url}")
