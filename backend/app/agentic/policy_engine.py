"""Static policy DAG for the Maya simulation flow.

No language model chooses tools. The validated graph is the authority for
execution order and dependency visibility.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyStep:
    id: str
    tool_name: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyPlan:
    policy_id: str
    version: str
    steps: tuple[PolicyStep, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for step in self.steps:
            if step.id in seen:
                raise ValueError(f"duplicate policy step: {step.id}")
            if any(dependency not in seen for dependency in step.depends_on):
                raise ValueError(f"policy dependency appears after step: {step.id}")
            seen.add(step.id)


MAYA_SIMULATION_POLICY = PolicyPlan(
    policy_id="maya.synthetic.simulation",
    version="1.0.0",
    steps=(
        PolicyStep("route", "route_simulator"),
        PolicyStep("readiness", "readiness_predictor", ("route",)),
        PolicyStep("supply", "stock_forecaster", ("route", "readiness")),
        PolicyStep("uncertainty", "uncertainty_engine", ("route", "readiness", "supply")),
        PolicyStep("evidence", "evidence_layer", ("uncertainty",)),
        PolicyStep("confidence", "confidence_engine", ("evidence",)),
    ),
)
MAYA_SIMULATION_POLICY.validate()


def select_policy(samples: int) -> PolicyPlan:
    """Select the deterministic policy; bounded inputs prevent arbitrary plans."""
    if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= 1000:
        raise ValueError("samples must be an integer from 1 to 1000")
    return MAYA_SIMULATION_POLICY
