from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aios.runtime.event_bus.base import EventBusProtocol, Events
from aios.runtime.models import PermissionAuditRecord, PermissionDecision, RiskLevel


class NoopEventBus:
    async def emit(self, event) -> None: ...


class PolicyProtocol:
    """A permission policy that defines rules for tool execution."""

    @property
    def name(self) -> str:
        return "default"

    async def evaluate(
        self,
        tool_name: str,
        args: dict[str, Any],
        risk_level: RiskLevel,
    ) -> PermissionDecision:
        return PermissionDecision.ALLOWED


class PermissionGate:
    """
    Decides whether a tool call is allowed, denied, or requires
    user confirmation.

    Internal pipeline:
      1. Policy         — load applicable rules from configured PolicyProtocol
      2. RiskAssessment — evaluate tool name + args → RiskLevel
      3. Decision       — apply policy + risk → PermissionDecision
      4. Audit          — log the decision to an in-memory audit trail
    """

    def __init__(self, event_bus: EventBusProtocol | None = None) -> None:
        self._policy: PolicyProtocol = PolicyProtocol()
        self._confirmation_callback: Callable[[str, dict[str, Any]], Awaitable[bool]] | None = None
        self._allowed_cache: set[str] = set()
        self._audit_log: list[PermissionAuditRecord] = []
        self._event_bus: EventBusProtocol = event_bus or NoopEventBus()

    async def check(self, tool_name: str, args: dict[str, Any]) -> PermissionDecision:
        cache_key = self._cache_key(tool_name, args)
        if cache_key in self._allowed_cache:
            return PermissionDecision.ALLOWED

        risk = self._assess_risk(tool_name, args)
        decision = await self._evaluate(tool_name, args, risk)
        reason = self._reason_for_decision(decision, risk)

        self._audit(tool_name, args, decision, risk, reason)

        await self._event_bus.emit(
            Events.PermissionAudit(
                tool_name=tool_name,
                risk_level=risk.value,
                decision=decision.value,
                policy_name=self._policy.name,
                reason=reason,
            )
        )

        return decision

    async def confirm(self, tool_name: str, args: dict[str, Any]) -> bool:
        if self._confirmation_callback is None:
            return False
        result = await self._confirmation_callback(tool_name, args)
        if result:
            self.remember_allow(tool_name, args)
        return result

    def set_policy(self, policy: PolicyProtocol) -> None:
        self._policy = policy

    def set_confirmation_callback(
        self,
        callback: Callable[[str, dict[str, Any]], Awaitable[bool]],
    ) -> None:
        self._confirmation_callback = callback

    def remember_allow(self, tool_name: str, args: dict[str, Any]) -> None:
        self._allowed_cache.add(self._cache_key(tool_name, args))

    def forget_allow(self, tool_name: str, args: dict[str, Any]) -> None:
        self._allowed_cache.discard(self._cache_key(tool_name, args))

    def get_audit_log(self) -> list[PermissionAuditRecord]:
        return list(self._audit_log)

    def _assess_risk(self, tool_name: str, args: dict[str, Any]) -> RiskLevel:
        DANGEROUS_TOOLS = {
            "filesystem_delete",
            "shell_exec",
            "command_run",
            "database_query",
            "file_write",
            "file_overwrite",
        }
        MODIFY_TOOLS = {
            "file_edit",
            "file_patch",
            "file_replace",
            "git_commit",
            "git_push",
            "npm_install",
        }

        if tool_name in DANGEROUS_TOOLS:
            return RiskLevel.CRITICAL
        if tool_name in MODIFY_TOOLS:
            return RiskLevel.HIGH
        if tool_name == "read_file" or tool_name == "search":
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    async def _evaluate(
        self,
        tool_name: str,
        args: dict[str, Any],
        risk: RiskLevel,
    ) -> PermissionDecision:
        if risk == RiskLevel.CRITICAL:
            return PermissionDecision.REQUIRES_CONFIRMATION
        if risk == RiskLevel.HIGH:
            return PermissionDecision.REQUIRES_CONFIRMATION
        policy_decision = await self._policy.evaluate(tool_name, args, risk)
        return policy_decision

    def _reason_for_decision(self, decision: PermissionDecision, risk: RiskLevel) -> str:
        if decision == PermissionDecision.ALLOWED:
            return f"Allowed (low risk: {risk.value})"
        if decision == PermissionDecision.DENIED:
            return f"Denied by policy (risk: {risk.value})"
        return f"Requires confirmation (risk: {risk.value})"

    def _audit(
        self,
        tool_name: str,
        args: dict[str, Any],
        decision: PermissionDecision,
        risk_level: RiskLevel,
        reason: str,
    ) -> None:
        record = PermissionAuditRecord(
            tool_name=tool_name,
            args=args,
            decision=decision,
            risk_level=risk_level,
            policy_name=self._policy.name,
            reason=reason,
        )
        self._audit_log.append(record)
        if len(self._audit_log) > 10_000:
            self._audit_log = self._audit_log[-5_000:]

    def _cache_key(self, tool_name: str, args: dict[str, Any]) -> str:
        import json

        return f"{tool_name}:{json.dumps(args, sort_keys=True, default=str)}"
