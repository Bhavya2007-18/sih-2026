"""Execution-quality scoring for synthetic outputs."""

from app.agentic.contracts import ConfidenceAssessment, ToolExecution
from app.models import Scenario


def assess_confidence(
    scenario: Scenario,
    samples: int,
    executions: list[ToolExecution],
    warnings: list[str] | None = None,
) -> ConfidenceAssessment:
    warnings = warnings or []
    fallback_count = sum(execution.fallback_used for execution in executions)
    factors = {
        # The Pydantic Scenario is validated before this point.
        "input_completeness": 1.0,
        # This is a run-coverage control, not a confidence interval.
        "simulation_stability": min(1.0, samples / 1000),
        # Coefficients are explicitly synthetic and uncalibrated.
        "model_quality": 0.35,
        # A local scenario is current at execution time, but is not live data.
        "data_freshness": 1.0,
        "uncertainty_control": min(1.0, samples / 1000),
        "fallback_usage": (
            0.0
            if fallback_count == 0
            else max(0.0, 1.0 - fallback_count / len(executions))
        ),
    }
    cap = factors["model_quality"]
    score = min(min(factors.values()), cap)
    reasons = [
        "Synthetic readiness and disruption coefficients are not calibrated to real-world data.",
    ]
    if samples < 1000:
        reasons.append("Sample count is below the bounded 1,000-trial reference workload.")
    if fallback_count:
        reasons.append(
            f"{fallback_count} tool execution(s) used a declared deterministic fallback."
        )
    reasons.extend(warnings)
    return ConfidenceAssessment(
        status="DEGRADED" if reasons else "NOMINAL",
        score=score,
        factors=factors,
        cap=cap,
        degraded_reasons=reasons,
    )
