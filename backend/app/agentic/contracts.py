"""Structured execution, evidence and quality-control contracts.

These are operational quality metadata, not claims of real-world prediction
accuracy. Domain values remain produced by the deterministic simulator.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class StructuredToolOutput(Contract):
    """Stable envelope for every future Maya tool adapter."""

    status: Literal["success", "degraded", "failed"]
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = Field(ge=0, default=0)


class ToolExecution(Contract):
    tool_name: str
    tool_version: str
    status: Literal["SUCCESS", "DEGRADED", "FAILED"]
    started_at: str
    execution_time_ms: float = Field(ge=0)
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    fallback_used: bool = False


class Fact(Contract):
    value: Any
    unit: str | None = None
    source_tool: str
    label: str


class FactSheet(Contract):
    generated_at: str
    facts: dict[str, Fact] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class ConfidenceAssessment(Contract):
    """Execution-quality indicator; never a probability of real-world success."""

    status: Literal["NOMINAL", "DEGRADED", "BLOCKED"]
    score: float = Field(ge=0, le=1)
    factors: dict[str, float] = Field(default_factory=dict)
    cap: float | None = Field(default=None, ge=0, le=1)
    degraded_reasons: list[str] = Field(default_factory=list)
    interpretation: str = (
        "Execution-quality control for synthetic simulation; not prediction accuracy, "
        "a confidence interval or a real-world reliability claim."
    )


class AuditEntry(Contract):
    sequence: int = Field(ge=1)
    event: str
    policy_id: str
    tool_name: str | None = None
    status: Literal["STARTED", "SUCCESS", "DEGRADED", "FAILED", "RESULT"]
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    at: str


class AuditTrace(Contract):
    policy_id: str
    status: Literal["SUCCESS", "DEGRADED", "FAILED"]
    entries: list[AuditEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class ExecutionMetadata(Contract):
    """All structured metadata attached to an immutable simulation result."""

    status: Literal["SUCCESS", "DEGRADED", "FAILED"]
    policy_id: str
    tool_executions: list[ToolExecution] = Field(default_factory=list)
    fact_sheet: FactSheet
    confidence: ConfidenceAssessment
    audit_trace: AuditTrace
