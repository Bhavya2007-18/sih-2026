"""Small builder for inspectable policy/tool execution traces."""

from datetime import UTC, datetime
from typing import Any, Literal

from app.agentic.contracts import AuditEntry, AuditTrace


def now() -> str:
    return datetime.now(UTC).isoformat()


class AuditBuilder:
    def __init__(self, policy_id: str, *, at: str | None = None) -> None:
        self.policy_id = policy_id
        self.at = at
        self.entries: list[AuditEntry] = []
        self.warnings: list[str] = []
        self.assumptions: list[str] = []

    def add(
        self,
        event: str,
        status: Literal["STARTED", "SUCCESS", "DEGRADED", "FAILED", "RESULT"],
        *,
        tool_name: str | None = None,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        assumptions: list[str] | None = None,
    ) -> None:
        entry = AuditEntry(
            sequence=len(self.entries) + 1,
            event=event,
            policy_id=self.policy_id,
            tool_name=tool_name,
            status=status,
            inputs=inputs or {},
            outputs=outputs or {},
            warnings=warnings or [],
            assumptions=assumptions or [],
            at=self.at or now(),
        )
        self.entries.append(entry)
        self.warnings.extend(entry.warnings)
        self.assumptions.extend(entry.assumptions)

    def build(self, status: Literal["SUCCESS", "DEGRADED", "FAILED"]) -> AuditTrace:
        return AuditTrace(
            policy_id=self.policy_id,
            status=status,
            entries=self.entries,
            warnings=list(dict.fromkeys(self.warnings)),
            assumptions=list(dict.fromkeys(self.assumptions)),
        )
