"""Policy-controlled simulation execution and evidence assembly."""

from typing import Literal

from app.agentic.audit_trace import AuditBuilder
from app.agentic.confidence_engine import assess_confidence
from app.agentic.contracts import Fact, FactSheet, ToolExecution
from app.agentic.fallback_manager import select_tool
from app.agentic.policy_engine import select_policy
from app.core.simulation import run_simulation_core
from app.models import Scenario, SimulationResult


def _facts(result: SimulationResult, generated_at: str) -> FactSheet:
    selected = next(
        (option for option in result.options if option.route.route_id == result.selected_route_id),
        None,
    )
    facts: dict[str, Fact] = {
        "route.selected_id": Fact(
            value=result.selected_route_id,
            source_tool="route_simulator",
            label="Selected route",
        ),
        "run.samples": Fact(
            value=result.samples,
            unit="trials",
            source_tool="uncertainty_engine",
            label="Simulation samples",
        ),
    }
    if selected:
        route = selected.route
        facts.update(
            {
                "route.eta_p50_hours": Fact(
                    value=route.eta_hours.median if route.eta_hours else None,
                    unit="hours",
                    source_tool="route_simulator",
                    label="ETA P50",
                ),
                "route.eta_p90_hours": Fact(
                    value=route.eta_hours.p90 if route.eta_hours else None,
                    unit="hours",
                    source_tool="uncertainty_engine",
                    label="ETA P90",
                ),
                "route.arrival_probability": Fact(
                    value=route.success_probability,
                    unit="fraction",
                    source_tool="route_simulator",
                    label="Arrival probability",
                ),
            }
        )
        destination = next(
            (
                forecast
                for forecast in selected.supply_forecast
                if forecast.node_id == result.data_resilience.get("destination_node_id")
            ),
            None,
        )
        if destination:
            initial_stock = (
                destination.stock_timeline[0].stock.median
                if destination.stock_timeline
                else None
            )
            facts.update(
                {
                    "stock.current_stock": Fact(
                        value=initial_stock,
                        unit="supply units",
                        source_tool="stock_forecaster",
                        label="Current stock",
                    ),
                    "stock.projected_stock": Fact(
                        value=destination.minimum_stock.median,
                        unit="supply units",
                        source_tool="stock_forecaster",
                        label="Projected stock",
                    ),
                    "stock.minimum_p50": Fact(
                        value=destination.minimum_stock.median,
                        unit="supply units",
                        source_tool="stock_forecaster",
                        label="Projected minimum stock",
                    ),
                    "stock.time_to_critical_p50_hours": Fact(
                        value=(
                            destination.time_to_critical_hours.median
                            if destination.time_to_critical_hours
                            else None
                        ),
                        unit="hours",
                        source_tool="stock_forecaster",
                        label="Time to critical stock",
                    ),
                    "stock.critical_threshold": Fact(
                        value=destination.critical_threshold,
                        unit="supply units",
                        source_tool="stock_forecaster",
                        label="Critical threshold",
                    ),
                    "stock.stockout_date": Fact(
                        value=destination.stockout_date,
                        source_tool="stock_forecaster",
                        label="Stockout date",
                    ),
                    "stock.stockout_probability": Fact(
                        value=destination.stockout_probability,
                        unit="fraction",
                        source_tool="stock_forecaster",
                        label="Stockout probability",
                    ),
                }
            )
        if selected.readiness:
            readiness = min(selected.readiness, key=lambda item: item.score)
            facts["readiness.minimum_score"] = Fact(
                value=readiness.score,
                unit="score / 100",
                source_tool="readiness_predictor",
                label="Lowest resource readiness",
            )
    return FactSheet(
        generated_at=generated_at,
        facts=facts,
        warnings=[],
        assumptions=list(result.assumptions),
    )


def execute_simulation(
    scenario: Scenario,
    samples: int,
    *,
    unavailable_tools: set[str] | None = None,
) -> SimulationResult:
    """Run the bounded deterministic core under the static policy DAG.

    The current domain engine is intentionally a pure coupled calculation. The
    policy layer records its module boundaries and controls declared fallback
    selection without allowing free-form model/tool decisions.
    """
    policy = select_policy(samples)
    unavailable_tools = unavailable_tools or set()
    # Result metadata is part of the deterministic immutable snapshot. The API
    # Run envelope carries wall-clock created_at separately.
    audit = AuditBuilder(policy.policy_id, at=scenario.start_time)
    executions: list[ToolExecution] = []
    warnings: list[str] = []
    audit.add(
        "simulation_started",
        "STARTED",
        inputs={"scenario_id": scenario.id, "samples": samples},
        assumptions=["Synthetic simulation only; no operational execution."],
    )
    selections = {}
    for step in policy.steps:
        selection = select_tool(step.tool_name, unavailable=unavailable_tools)
        selections[step.id] = selection
        if selection.warning:
            warnings.append(selection.warning)
        audit.add(
            f"{step.id}_started",
            "STARTED",
            tool_name=selection.selected.name,
            inputs={
                "scenario_id": scenario.id,
                "samples": samples,
                "depends_on": list(step.depends_on),
            },
        )

    try:
        result = run_simulation_core(scenario, samples)
    except Exception as exc:
        audit.add("simulation_failed", "FAILED", outputs={"error": str(exc)}, warnings=[str(exc)])
        raise

    generated_at = scenario.start_time
    fact_sheet = _facts(result, generated_at)
    for step in policy.steps:
        selection = selections[step.id]
        fallback_used = selection.fallback_used
        status: Literal["DEGRADED", "SUCCESS"] = "DEGRADED" if fallback_used else "SUCCESS"
        step_outputs = {
            "route": [route.route_id for route in result.route_results],
            "readiness": [item.resource_id for item in result.readiness_results],
            "supply": [item.node_id for item in result.supply_forecast],
            "uncertainty": list(result.uncertainty),
            "evidence": list(fact_sheet.facts),
            "confidence": ["execution_quality_score"],
        }
        output_keys = step_outputs[step.id]
        executions.append(
            ToolExecution(
                tool_name=selection.selected.name,
                tool_version=selection.selected.version,
                status=status,
                started_at=generated_at,
                execution_time_ms=0.0,
                inputs={"scenario_id": scenario.id, "samples": samples},
                outputs=output_keys,
                warnings=[selection.warning] if selection.warning else [],
                assumptions=[
                    "Outputs are produced by the deterministic synthetic domain engine.",
                    "Wall-clock execution timing is recorded in the API Run envelope, "
                    "not this deterministic result snapshot.",
                ],
                fallback_used=fallback_used,
            )
        )
        audit.add(
            f"{step.id}_completed",
            status,
            tool_name=selection.selected.name,
            outputs={"keys": output_keys},
            warnings=[selection.warning] if selection.warning else [],
        )
    confidence = assess_confidence(scenario, samples, executions, warnings)
    final_status: Literal["SUCCESS", "DEGRADED", "FAILED"] = (
        "DEGRADED" if warnings or confidence.status == "DEGRADED" else "SUCCESS"
    )
    audit.add(
        "result_ready",
        "RESULT",
        outputs={
            "selected_route_id": result.selected_route_id,
            "fact_count": len(fact_sheet.facts),
            "confidence_score": confidence.score,
        },
        warnings=warnings,
    )
    metadata = {
        "execution_status": final_status,
        "policy_id": policy.policy_id,
        "tool_executions": executions,
        "fact_sheet": fact_sheet,
        "confidence": confidence,
        "audit_trace": audit.build(final_status),
    }
    return result.model_copy(update=metadata)
