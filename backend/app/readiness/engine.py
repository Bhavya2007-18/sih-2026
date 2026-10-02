"""An explicit linear toy model: prior rest is credited once, workload grows with travel."""

from app.models import ReadinessConfig, ReadinessPoint, ReadinessResult, Resource, Route


def factors(
    resource: Resource, route: Route, duration: float, config: ReadinessConfig
) -> dict[str, float]:
    """Signed terms sum to the raw score; clamping is an explicit contribution."""
    contributions = {
        "base_readiness": float(resource.base_readiness),
        "load": -config.load_penalty * resource.load / resource.capacity,
        "duration": -config.duration_penalty_per_hour * duration,
        "workload": -config.workload_penalty_per_hour * (resource.operating_hours + duration),
        "rest": min(config.max_rest_recovery, config.rest_recovery_per_hour * resource.rest_hours),
        "environment": -config.environment_penalty * route.environment_stress,
        "altitude": -config.altitude_penalty * route.altitude_stress,
    }
    raw = sum(contributions.values())
    contributions["clamping"] = min(100.0, max(0.0, raw)) - raw
    return contributions


def readiness_score(
    resource: Resource, route: Route, duration: float, config: ReadinessConfig
) -> float:
    """Score in [0, 100]; the travel duration includes sampled and event delays."""
    return sum(factors(resource, route, duration, config).values())


def resource_feasible(
    resource: Resource, route: Route, duration: float, config: ReadinessConfig
) -> bool:
    return resource.load <= resource.capacity and (
        readiness_score(resource, route, duration, config) >= config.feasibility_threshold
    )


def evaluate_readiness(
    resource: Resource,
    route: Route,
    duration: float,
    config: ReadinessConfig,
    step_hours: float,
) -> ReadinessResult:
    """Representative timeline for one duration, not a sampled readiness interval.

    Feasible at equality with the threshold. time_to_threshold is the infimum
    of travel times with score BELOW the threshold; null if not below by arrival.
    """
    contributions = factors(resource, route, duration, config)
    score = sum(contributions.values())
    state = (
        "GREEN"
        if score >= config.green_threshold
        else "AMBER"
        if score >= config.amber_threshold
        else "RED"
    )
    initial_raw = sum(factors(resource, route, 0, config).values())
    # Before clamping, resting above 100 still offsets later workload.
    initial_terms = factors(resource, route, 0, config)
    initial_raw -= initial_terms["clamping"]
    decay = config.duration_penalty_per_hour + config.workload_penalty_per_hour
    threshold_time = None
    if score < config.feasibility_threshold:
        threshold_time = (
            max(0.0, (initial_raw - config.feasibility_threshold) / decay) if decay else 0.0
        )
    hours = {0.0, duration}
    hour = step_hours
    # Avoid unbounded reporting loops for extremely large user-supplied delays.
    # The scenario horizon is bounded to 336h; still include the actual endpoint.
    while hour < min(duration, 336.0):
        hours.add(hour)
        hour += step_hours
    if threshold_time is not None:
        hours.add(threshold_time)
    return ReadinessResult(
        resource_id=resource.id,
        score=score,
        state=state,
        feasible=resource_feasible(resource, route, duration, config),
        time_to_threshold_hours=threshold_time,
        factor_contributions=contributions,
        timeline=[
            ReadinessPoint(hour=hour, score=readiness_score(resource, route, hour, config))
            for hour in sorted(hours)
        ],
    )
