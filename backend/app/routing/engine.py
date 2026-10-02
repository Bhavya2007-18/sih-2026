"""Synthetic route travel times and hard movement constraints."""

from app.models import Route, Scenario
from app.uncertainty.sampler import stream


def sample_duration(route: Route, seed: int, trial: int, delay_hours: float = 0) -> float:
    """Segment independent uniform jitter plus independent Bernoulli additive delay."""
    total = delay_hours
    for segment in route.segments:
        jitter = stream(seed, "route", route.id, "segment", segment.id, "travel", trial).random()
        disruption = stream(seed, "route", route.id, "segment", segment.id, "delay", trial).random()
        total += segment.nominal_hours * (1 + segment.time_variation_fraction * (2 * jitter - 1))
        if disruption < segment.disruption_probability:
            total += segment.disruption_delay_hours
    return total


def movement_constraints(route: Route, scenario: Scenario) -> list[str]:
    """All consignments share the same assigned resource load; no hidden extra trips."""
    failures: list[str] = []
    load = sum(resource.load for resource in scenario.resources)
    inbound = sum(
        shipment.quantity for node in scenario.stock_nodes for shipment in node.scheduled_inbound
    )
    if not all(segment.available for segment in route.segments):
        failures.append("At least one candidate segment is unavailable.")
    if any(resource.load > resource.capacity for resource in scenario.resources):
        failures.append("An assigned resource is overloaded (load exceeds capacity).")
    if load > route.capacity:
        failures.append("Aggregate assigned load exceeds candidate route capacity.")
    if inbound > load:
        failures.append("Aggregate inbound quantity exceeds aggregate assigned resource load.")
    return failures
