from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aios.runtime.models import PermissionAuditRecord, PermissionDecision, RiskLevel


class PolicyProtocol:
    """A permission policy that defines rules for tool execution."""

    @property
    def name(self) -> str:
        """Return the policy name."""

    async def evaluate(
        self,
        tool_name: str,
        args: dict[str, Any],
        risk_level: RiskLevel,
    ) -> PermissionDecision:
        """Evaluate whether a tool call is allowed given its risk level."""


class PermissionGateProtocol:
    """
    Decides whether a tool call is allowed, denied, or requires
    user confirmation.

    Internal pipeline (implemented in Phase 2):

      1. Policy        — load applicable rules from the configured PolicyProtocol
      2. RiskAssessment — evaluate tool name + args → RiskLevel
      3. Decision      — apply policy + risk → PermissionDecision
      4. Audit         — log the decision to an in-memory audit trail
    """

    async def check(self, tool_name: str, args: dict[str, Any]) -> PermissionDecision:
        """Check whether a tool call is allowed. Runs the full policy pipeline."""

    async def confirm(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Ask the user for confirmation. Returns True if approved."""

    def set_policy(self, policy: PolicyProtocol) -> None:
        """Set the permission policy."""

    def set_confirmation_callback(
        self,
        callback: Callable[[str, dict[str, Any]], Awaitable[bool]],
    ) -> None:
        """Set the user confirmation callback."""

    def remember_allow(self, tool_name: str, args: dict[str, Any]) -> None:
        """Remember that a tool call was allowed for future auto-approval."""

    def forget_allow(self, tool_name: str, args: dict[str, Any]) -> None:
        """Forget a previously remembered allow decision."""

    def get_audit_log(self) -> list[PermissionAuditRecord]:
        """Return the full audit log of all permission decisions."""
