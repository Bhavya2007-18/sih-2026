"""At-start changes applied in input order to a deep copy of the saved snapshot."""

from dataclasses import dataclass

from app.models import Scenario


@dataclass(frozen=True)
class AppliedEvents:
    scenario: Scenario
    route_delays: dict[str, float]


def apply_events(scenario: Scenario) -> AppliedEvents:
    """Delay adds hours; demand/load/rest/environment replace their absolute inputs.

    Separate deterministic delays preserve the baseline travel-variation draws.
    Stored event lists are not removed or reapplied inside a run.
    """
    updated = scenario.model_copy(deep=True)
    delays = dict.fromkeys((route.id for route in updated.routes), 0.0)
    routes = {route.id: route for route in updated.routes}
    resources = {resource.id: resource for resource in updated.resources}
    stocks = {stock.node_id: stock for stock in updated.stock_nodes}
    for event in updated.events:
        if event.start_hour != 0:
            raise ValueError("only at-start events are supported")
        match event.type:
            case "ROUTE_DELAY":
                delays[event.target] += event.magnitude
            case "ROUTE_UNAVAILABLE":
                for segment in routes[event.target].segments:
                    segment.available = False
            case "DEMAND_CHANGE":
                stocks[event.target].daily_consumption = event.magnitude
            case "ENVIRONMENT_CHANGE":
                routes[event.target].environment_stress = event.magnitude
            case "LOAD_CHANGE":
                resources[event.target].load = event.magnitude
            case "REST_CHANGE":
                resources[event.target].rest_hours = event.magnitude
            case "CONNECTIVITY_LOSS":
                updated.connectivity_online = False
            case "CONNECTIVITY_RESTORE":
                updated.connectivity_online = True
    return AppliedEvents(scenario=updated, route_delays=delays)
