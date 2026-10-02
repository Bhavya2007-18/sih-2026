"""Comparison of immutable simulation outputs; no resimulation or UI-side math."""

from typing import TypedDict

from app.models import SimulationResult, StockForecast

Scalar = str | float | bool | None


class Change(TypedDict):
    metric: str
    before: Scalar
    after: Scalar
    delta: float | None


class Comparison(TypedDict):
    changes: list[Change]
    explanation: list[str]


def _destination(result: SimulationResult) -> StockForecast | None:
    destination = result.data_resilience.get("destination_node_id")
    if isinstance(destination, str):
        return next((node for node in result.supply_forecast if node.node_id == destination), None)
    # Legacy output without the explicit destination key only has one stock node.
    return result.supply_forecast[0] if len(result.supply_forecast) == 1 else None


def _metrics(result: SimulationResult) -> dict[str, Scalar]:
    route = next(
        (route for route in result.route_results if route.route_id == result.selected_route_id),
        None,
    )
    stock = _destination(result)
    return {
        "route": result.selected_route_id,
        "eta_hours": route.eta_hours.median if route and route.eta_hours else None,
        "readiness_score": min((item.score for item in result.readiness_results), default=None),
        "minimum_stock": stock.minimum_stock.median if stock else None,
        "time_to_critical_hours": (
            stock.time_to_critical_hours.median if stock and stock.time_to_critical_hours else None
        ),
        "shortage_quantity": stock.shortage_quantity.median if stock else None,
        "connectivity_online": result.data_resilience.get("connectivity_online"),
    }


def compare_runs(baseline: SimulationResult, what_if: SimulationResult) -> Comparison:
    """The API adds run IDs; numeric deltas are after-before, never categorical deltas."""
    before = _metrics(baseline)
    after = _metrics(what_if)
    changes: list[Change] = []
    explanation = []
    for metric in before:
        old, new = before[metric], after[metric]
        delta = (
            float(new) - float(old)
            if isinstance(old, (int, float))
            and not isinstance(old, bool)
            and isinstance(new, (int, float))
            and not isinstance(new, bool)
            else None
        )
        changes.append(Change(metric=metric, before=old, after=new, delta=delta))
        if old != new:
            explanation.append(
                f"{metric}: {old} -> {new}"
                + (f" (after - before = {delta:+.4g})." if delta is not None else ".")
            )
    if not explanation:
        explanation.append("No change in the reported selected-option median metrics.")
    if what_if.selected_route_id is None:
        explanation.append(
            "No candidate succeeds in sampled hard constraints; forecast has no inbound."
        )
    explanation.append(
        "Candidate travel duration feeds trial readiness, then successful inbound "
        "arrivals and stock. Comparisons summarize selected options; a route switch "
        "also changes the resource conditions."
    )
    explanation.append(
        "ETA medians condition on movement success. Critical-time medians condition "
        "on within-horizon crossings, so null means no observed event, not a zero-hour "
        "date. Inspect event probabilities "
        "and sample bands; differences are not confidence intervals."
    )
    if baseline.seed != what_if.seed or baseline.samples != what_if.samples:
        explanation.append(
            "Seeds or sample counts differ; comparisons are not fully paired trials."
        )
    return Comparison(changes=changes, explanation=explanation)
