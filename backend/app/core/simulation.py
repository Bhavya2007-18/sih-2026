"""Pure, seeded route -> readiness -> actual delivery -> stock orchestration."""

from app.core.comparison import compare_runs as compare_runs
from app.core.events import apply_events
from app.models import Option, Route, RouteResult, Scenario, SimulationResult, StockForecast
from app.readiness.engine import evaluate_readiness, resource_feasible
from app.routing.engine import movement_constraints, sample_duration
from app.supply.forecast import StockTrial, forecast_stock, summarize_forecast
from app.uncertainty.sampler import sample_demand
from app.uncertainty.summarizer import percentile, summarize


def _stock_forecasts(
    scenario: Scenario,
    demands: dict[str, list[float]],
    durations: list[float],
    successes: list[bool],
) -> list[StockForecast]:
    forecasts = []
    for node in scenario.stock_nodes:
        trials: list[StockTrial] = []
        for trial, duration in enumerate(durations):
            arrivals = (
                [
                    (shipment.departure_hour + duration, shipment.quantity)
                    for shipment in node.scheduled_inbound
                ]
                if successes[trial]
                else []
            )
            trials.append(
                forecast_stock(
                    node,
                    demands[node.node_id][trial],
                    arrivals,
                    scenario.horizon_hours,
                    scenario.step_hours,
                )
            )
        forecasts.append(summarize_forecast(node, trials, scenario.start_time))
    return forecasts


def _evaluate_route(
    scenario: Scenario, route: Route, demands: dict[str, list[float]], samples: int, delay: float
) -> Option:
    durations = [sample_duration(route, scenario.seed, trial, delay) for trial in range(samples)]
    failures = movement_constraints(route, scenario)
    successes = [
        not failures
        and duration <= scenario.horizon_hours
        and all(
            resource_feasible(resource, route, duration, scenario.readiness_config)
            for resource in scenario.resources
        )
        for duration in durations
    ]
    successful_durations = [
        duration for duration, success in zip(durations, successes, strict=True) if success
    ]
    success_probability = len(successful_durations) / samples
    supply = _stock_forecasts(scenario, demands, durations, successes)
    destination = next(node for node in supply if node.node_id == scenario.destination)
    median_duration = percentile(durations, 0.5)
    time_cost = scenario.scoring.time_weight * median_duration / scenario.horizon_hours
    failure_cost = scenario.scoring.failure_weight * (1 - success_probability)
    stock_cost = scenario.scoring.critical_stock_weight * destination.critical_probability
    drivers = [
        *failures,
        f"Time cost: {scenario.scoring.time_weight:g} * attempted median duration "
        f"{median_duration:.4g} / horizon {scenario.horizon_hours:g} = {time_cost:.4g}.",
        f"Failure cost: {scenario.scoring.failure_weight:g} * (1 - success fraction "
        f"{success_probability:.4g}) = {failure_cost:.4g}.",
        f"Critical-stock cost: {scenario.scoring.critical_stock_weight:g} * destination "
        f"critical fraction {destination.critical_probability:.4g} = {stock_cost:.4g}.",
        "Lower total score ranks better; feasibility requires at least one successful trial.",
        "Readiness shown at median attempted duration; each delivery uses its own trial readiness.",
    ]
    if any(duration > scenario.horizon_hours for duration in durations):
        drivers.append("Over-horizon movement trials deliver no inbound supply.")
    if any(
        not resource_feasible(resource, route, duration, scenario.readiness_config)
        for duration in durations
        for resource in scenario.resources
    ):
        drivers.append("Trials failing a resource capacity/readiness constraint deliver no supply.")
    if any(
        shipment.departure_hour + duration > scenario.horizon_hours
        for node in scenario.stock_nodes
        for shipment in node.scheduled_inbound
        for duration in successful_durations
    ):
        drivers.append("Consignments arriving after the horizon are excluded, not delivered early.")
    return Option(
        route=RouteResult(
            route_id=route.id,
            distance_km=sum(segment.distance_km for segment in route.segments),
            nominal_hours=sum(segment.nominal_hours for segment in route.segments) + delay,
            eta_hours=summarize(successful_durations) if successful_durations else None,
            success_probability=success_probability,
            resilience_score=100 * success_probability,
            feasible=bool(successful_durations),
            score=time_cost + failure_cost + stock_cost,
            drivers=drivers,
        ),
        readiness=[
            evaluate_readiness(
                resource, route, median_duration, scenario.readiness_config, scenario.step_hours
            )
            for resource in scenario.resources
        ],
        supply_forecast=supply,
    )


def run_simulation_core(scenario: Scenario, samples: int) -> SimulationResult:
    """Run 1..1000 synthetic trials without mutation, I/O, or global random state.

    Candidate route streams and node-demand streams are keyed by IDs, seed and
    trial (not scenario ID). Common random numbers pair baseline/what-if runs.
    The recommendation minimizes documented cost among sampled-feasible routes.
    """
    if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= 1000:
        raise ValueError("samples must be an integer from 1 to 1000")
    applied = apply_events(scenario)
    updated = applied.scenario
    demands = {
        node.node_id: [
            sample_demand(
                updated.seed,
                trial,
                node.node_id,
                node.daily_consumption,
                node.demand_variation_fraction,
            )
            for trial in range(samples)
        ]
        for node in updated.stock_nodes
    }
    options = [
        _evaluate_route(updated, route, demands, samples, applied.route_delays[route.id])
        for route in updated.routes
    ]
    options.sort(
        key=lambda option: (not option.route.feasible, option.route.score, option.route.route_id)
    )
    selected = next((option for option in options if option.route.feasible), None)
    forecasts = (
        selected.supply_forecast
        if selected
        else _stock_forecasts(updated, demands, [0.0] * samples, [False] * samples)
    )
    return SimulationResult(
        scenario_id=scenario.id,
        seed=updated.seed,
        samples=samples,
        selected_route_id=selected.route.route_id if selected else None,
        options=options,
        route_results=[option.route for option in options],
        readiness_results=selected.readiness if selected else [],
        supply_forecast=forecasts,
        assumptions=assumption_ledger(updated, applied.route_delays, samples),
        uncertainty={
            "interval_type": "Empirical P10/P50/P90 with linear interpolation; "
            "not confidence intervals.",
            "eta": "Travel hours conditional on successful movement trials only; "
            "null if none succeed.",
            "success_probability": "Sample fraction completing within horizon and all "
            "hard constraints; not calibrated real-world reliability or a guarantee "
            "that every later consignment arrives.",
            "crossing_times": "Critical/stockout intervals and ISO dates condition on "
            "crossing within horizon; probabilities include ALL trials. "
            "Non-crossings are right-censored.",
            "readiness": "Single median-attempted-duration representative and timeline, not a "
            "readiness percentile interval. Actual delivery feasibility is evaluated per sample.",
            "drivers": "Independent segment uniform travel variation and Bernoulli "
            "additive delays; one uniform daily demand draw per node/trial, "
            "shared across candidate routes.",
        },
        data_resilience={
            "connectivity_online": updated.connectivity_online,
            "destination_node_id": updated.destination,
            "status": "ONLINE" if updated.connectivity_online else "OFFLINE",
            "simulation_continuity": "Connectivity changes do not alter local physical simulation.",
            "reconciliation": "No reconciliation performed by this pure simulator; use record API.",
        },
    )


def run_simulation(scenario: Scenario, samples: int) -> SimulationResult:
    """Execute the pure core through Maya's deterministic policy layer."""
    from app.agentic.execution import execute_simulation

    return execute_simulation(scenario, samples)


def assumption_ledger(
    scenario: Scenario, route_delays: dict[str, float], samples: int
) -> list[str]:
    """Record toy-model terms and input-dependent assumptions, not confidence claims."""
    config = scenario.readiness_config
    ledger = [
        *scenario.assumptions,
        "Fictional synthetic logistics only; no operational execution, medical claims, trained ML "
        "or real-world calibration.",
        f"Seed={scenario.seed}; samples={samples}; start={scenario.start_time}; "
        f"horizon={scenario.horizon_hours:g}h inclusive; reporting step={scenario.step_hours:g}h.",
        "Explicit candidate segment routes only; no graph-path generation, fuel, hidden losses, "
        "additional trips or resource-type-specific capability factors.",
        "Stable SHA-256 keyed standard-library Random streams: seed/node/trial demand and "
        "seed/route/segment/trial travel and disruption; scenario ID and route order are excluded.",
        "Each node's daily demand is drawn ONCE per trial as Uniform(daily*(1-f), daily*(1+f)), "
        "held constant over time and shared between candidate routes. Segment travel independently "
        "uses nominal*(1+Uniform(-f,f)); Bernoulli(p) adds the configured delay hours.",
        "At-start events run in input order on a deep copy: ROUTE_DELAY adds deterministic hours; "
        "ROUTE_UNAVAILABLE closes all target segments; DEMAND_CHANGE replaces units/day; "
        "LOAD_CHANGE replaces units; REST_CHANGE replaces hours; ENVIRONMENT_CHANGE replaces "
        "the normalized index. Connectivity loss/restore only toggles data state.",
        "Every inbound quantity shares aggregate assigned resource load. Total inbound > total "
        "load, any resource load > its capacity, or total load > route capacity "
        "blocks ALL delivery.",
        "Each trial's sampled travel duration drives readiness and arrival. "
        "Unavailable, overloaded, "
        "readiness-failed or movement-duration > horizon trials contribute NO inbound. Successful "
        "shipments arrive at departure_hour + travel duration; arrivals beyond "
        "horizon are excluded. "
        "Departure waiting is not counted as travel workload; no failed partial deliveries.",
        "Raw readiness(t) = base - load_penalty*(load/capacity) - duration_penalty_per_hour*t "
        "- workload_penalty_per_hour*(operating_hours+t) + min(max_rest_recovery, "
        "rest_recovery_per_hour*rest_hours) - environment_penalty*environment_stress "
        "- altitude_penalty*altitude_stress; clamp raw to [0,100]. Rest is credited "
        "once, not per step.",
        f"Exact readiness coefficients: load={config.load_penalty:g}; duration/h="
        f"{config.duration_penalty_per_hour:g}; workload/h={config.workload_penalty_per_hour:g}; "
        f"rest/h={config.rest_recovery_per_hour:g}; rest cap={config.max_rest_recovery:g}; "
        f"environment={config.environment_penalty:g}; altitude={config.altitude_penalty:g}.",
        f"Readiness GREEN >= {config.green_threshold:g}, AMBER >= {config.amber_threshold:g}, "
        f"otherwise RED; feasible >= {config.feasibility_threshold:g} inclusive. Threshold time "
        "is the infimum of times BELOW feasibility; null if never below by travel completion. "
        "Colors are independent of feasibility. Timelines use sampled median attempted duration "
        "(not a readiness band); regular timeline points stop at 336h for very long attempts.",
        "Physical stock is nonnegative and a fixed reserved quantity is protected "
        "from consumption. "
        "Forecasts, thresholds and days of supply use usable=physical-reserved. Demand is daily/24 "
        "per hour, continuously consumed between exact arrivals. No demand backlog: unmet demand "
        "accumulates as shortage and is never erased by replenishment.",
        "Critical is usable <= critical threshold; stockout is usable = 0, "
        "including initial stock. "
        "An exact threshold/arrival tie records the pre-arrival crossing; plotted grid values are "
        "post-arrival. Minimum includes within-step pre-arrival minima. Zero-demand DoS is null.",
        "P10/P50/P90 use sorted actual sample values and linear interpolation at (n-1)*p. They "
        "describe synthetic variability, NOT confidence intervals. ETA conditions on success; "
        "critical/stockout times and dates condition on observed events within horizon, while "
        "event probabilities divide by ALL samples. Non-events are right-censored, not imputed.",
        f"Ranking cost (lower is better) = {scenario.scoring.time_weight:g}*median attempted "
        f"duration/horizon + {scenario.scoring.failure_weight:g}*(1-success fraction) + "
        f"{scenario.scoring.critical_stock_weight:g}*destination critical fraction. Resilience=100*"
        "success fraction. Feasible means at least one successful sampled trial, not guaranteed "
        "delivery; ties use route ID. No feasible candidate => no recommendation, "
        "no inbound forecast.",
    ]
    for route in sorted(scenario.routes, key=lambda item: item.id):
        ledger.append(
            f"Route {route.id}: capacity={route.capacity:g}; "
            f"environment={route.environment_stress:g}; altitude={route.altitude_stress:g}; "
            f"at-start additive delay={route_delays[route.id]:g}h."
        )
        for segment in route.segments:
            ledger.append(
                f"Segment {route.id}/{segment.id}: available={segment.available}; "
                f"distance={segment.distance_km:g}km; nominal={segment.nominal_hours:g}h; "
                f"uniform travel fraction={segment.time_variation_fraction:g}; Bernoulli "
                f"delay p={segment.disruption_probability:g}; additive delay="
                f"{segment.disruption_delay_hours:g}h."
            )
    for resource in sorted(scenario.resources, key=lambda item: item.id):
        ledger.append(
            f"Resource {resource.id}: type={resource.resource_type}; "
            f"base={resource.base_readiness:g}; "
            f"capacity={resource.capacity:g}; load={resource.load:g}; prior operating="
            f"{resource.operating_hours:g}h; prior rest={resource.rest_hours:g}h."
        )
    for node in sorted(scenario.stock_nodes, key=lambda item: item.node_id):
        ledger.append(
            f"Stock node {node.node_id}: physical={node.stock:g}; "
            f"reserved={node.reserved_stock:g}; "
            f"daily consumption={node.daily_consumption:g}; uniform demand fraction="
            f"{node.demand_variation_fraction:g}; safety={node.safety_threshold:g}; "
            f"critical={node.critical_threshold:g}."
        )
        for inbound in node.scheduled_inbound:
            ledger.append(
                f"Inbound {node.node_id}/{inbound.id}: quantity={inbound.quantity:g}; "
                f"departure={inbound.departure_hour:g}h; all use the candidate movement."
            )
    return ledger
