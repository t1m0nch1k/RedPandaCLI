from __future__ import annotations

import json
from typing import Any

from aios.config.settings import CONFIG_DIR
from aios.permissions.base import PermissionDecision
from aios.permissions.policy import PermissionPolicy

PERMISSIONS_FILE = CONFIG_DIR / "permissions.json"

class PermissionManager:
    """
    Manages permissions by coordinating policies and persistent always-allow rules.
    """
    def __init__(self, policy: PermissionPolicy) -> None:
        self.policy = policy
        self._always_allow_cache: set[str] = self._load_always_allow()

    def _generate_call_hash(self, tool_name: str, args: dict[str, Any]) -> str:
        """Generates a unique string identifying the tool call."""
        # Sort keys to ensure consistency
        sorted_args = sorted(args.items())
        return f"{tool_name}:{json.dumps(sorted_args)}"

    def _load_always_allow(self) -> set[str]:
        if not PERMISSIONS_FILE.exists():
            return set()
        try:
            with open(PERMISSIONS_FILE) as f:
                return set(json.load(f))
        except (OSError, json.JSONDecodeError):
            return set()

    def _save_always_allow(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(PERMISSIONS_FILE, "w") as f:
            json.dump(list(self._always_allow_cache), f)

    def check(self, tool_name: str, args: dict[str, Any]) -> PermissionDecision:
        """
        Evaluates the permission for a given tool call.
        Priority:
        1. Always-Allow Cache
        2. Policy Rules
        3. Default (ASK)
        """
        call_hash = self._generate_call_hash(tool_name, args)
        if call_hash in self._always_allow_cache:
            return PermissionDecision.ALLOW
        
        return self.policy.evaluate(tool_name, args)

    def remember_allow(self, tool_name: str, args: dict[str, Any]) -> None:
        """Persistently marks a tool call as allowed."""
        call_hash = self._generate_call_hash(tool_name, args)
        self._always_allow_cache.add(call_hash)
        self._save_always_allow()

    def forget_allow(self, tool_name: str, args: dict[str, Any]) -> None:
        """Removes a tool call from the always-allow cache."""
        call_hash = self._generate_call_hash(tool_name, args)
        if call_hash in self._always_allow_cache:
            self._always_allow_cache.remove(call_hash)
            self._save_always_allow()
