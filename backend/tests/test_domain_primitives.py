"""Pure readiness, stock accounting and empirical-summary boundary tests."""

import random

import pytest

from app.models import ReadinessConfig, Resource, Route, Segment, StockNode
from app.readiness.engine import evaluate_readiness, readiness_score
from app.supply.forecast import forecast_stock, summarize_forecast, time_grid
from app.uncertainty.summarizer import percentile, summarize


def stock_node(**changes: float) -> StockNode:
    values = {
        "stock": 10.0,
        "reserved_stock": 0.0,
        "daily_consumption": 24.0,
        "safety_threshold": 3.0,
        "critical_threshold": 1.0,
        **changes,
    }
    return StockNode(node_id="destination", **values)


def route() -> Route:
    return Route(
        id="route",
        origin="origin",
        destination="destination",
        capacity=100,
        segments=[Segment(id="segment", distance_km=10, nominal_hours=10)],
    )


def test_exact_within_step_arrival_and_critical_crossing() -> None:
    node = stock_node(stock=4)
    trial = forecast_stock(node, 24, [(3.5, 10)], 8, 6)
    assert trial.hours == (0, 6, 8)
    assert trial.usable_stock == pytest.approx((4, 8, 6))
    assert trial.minimum_stock == pytest.approx(0.5)
    assert trial.critical_hour == pytest.approx(3)
    assert trial.stockout_hour is None
    assert trial.shortage_quantity == 0


def test_simultaneous_threshold_arrival_is_inclusive_before_replenishment() -> None:
    trial = forecast_stock(stock_node(stock=4), 24, [(3, 10)], 6, 6)
    assert trial.critical_hour == 3
    assert trial.minimum_stock == 1
    assert trial.usable_stock[-1] == 8
    assert trial.stockout_hour is None


def test_simultaneous_stockout_arrival_records_zero_but_not_unmet_demand() -> None:
    trial = forecast_stock(stock_node(stock=4), 24, [(4, 10)], 6, 6)
    assert trial.stockout_hour == 4
    assert trial.minimum_stock == 0
    assert trial.shortage_quantity == 0
    assert trial.usable_stock[-1] == 8


def test_reserve_is_protected_and_shortage_is_not_negative_stock() -> None:
    trial = forecast_stock(stock_node(stock=10, reserved_stock=8), 24, [], 6, 6)
    assert trial.usable_stock == (2, 0)
    assert trial.critical_hour == 1
    assert trial.stockout_hour == 2
    assert trial.final_physical_stock == 8
    assert trial.consumed_quantity == 2
    assert trial.shortage_quantity == 4


def test_later_delivery_never_erases_cumulative_unmet_demand() -> None:
    trial = forecast_stock(stock_node(stock=1), 24, [(4, 10)], 6, 6)
    assert trial.shortage_quantity == 3
    assert trial.consumed_quantity == 3
    assert trial.usable_stock[-1] == 8
    assert trial.final_physical_stock == 8


@pytest.mark.parametrize("opening,critical,stockout", [(0, 0, 0), (1, 0, None), (2, None, None)])
def test_initial_boundary_and_zero_demand(
    opening: float, critical: float | None, stockout: float | None
) -> None:
    node = stock_node(stock=opening, daily_consumption=0)
    trial = forecast_stock(node, 0, [], 10, 6)
    assert trial.critical_hour == critical
    assert trial.stockout_hour == stockout
    assert trial.shortage_quantity == 0
    assert trial.usable_stock == (opening,) * 3
    forecast = summarize_forecast(node, [trial], "2026-10-02T05:00:00+05:00")
    assert all(point.days_of_supply is None for point in forecast.stock_timeline)
    if critical == 0:
        assert forecast.critical_date == "2026-10-02T05:00:00+05:00"
    else:
        assert forecast.critical_date is None


def test_initial_reserve_and_zero_time_delivery_boundary() -> None:
    trial = forecast_stock(stock_node(stock=4, reserved_stock=4), 0, [(0, 10)], 6, 6)
    assert trial.critical_hour == trial.stockout_hour == 0
    assert trial.minimum_stock == 0
    assert trial.usable_stock == (10, 10)
    assert trial.final_physical_stock == 14


def test_arrival_on_horizon_counts_and_after_horizon_does_not() -> None:
    trial = forecast_stock(stock_node(stock=0), 0, [(6, 2), (6.001, 100)], 6, 6)
    assert trial.usable_stock[-1] == 2
    assert trial.delivered_quantity == 2


def test_conditional_crossing_bands_keep_probability_denominator() -> None:
    node = stock_node(stock=4)
    crossing = forecast_stock(node, 24, [], 10, 6)
    censored = forecast_stock(node, 0, [], 10, 6)
    forecast = summarize_forecast(node, [crossing, censored], "2026-10-02T00:00:00Z")
    assert forecast.critical_probability == forecast.stockout_probability == 0.5
    assert forecast.time_to_critical_hours is not None
    assert forecast.time_to_critical_hours.model_dump() == {"median": 3, "p10": 3, "p90": 3}
    assert forecast.critical_date == "2026-10-02T03:00:00+00:00"
    assert forecast.stockout_date == "2026-10-02T04:00:00+00:00"


def test_conservation_over_varied_arrivals_and_reserves() -> None:
    rng = random.Random(123)
    for _ in range(100):
        opening = rng.uniform(0, 20)
        reserve = rng.uniform(0, opening)
        demand = rng.uniform(0, 100)
        arrivals = [(rng.uniform(0, 30), rng.uniform(0, 20)) for _ in range(5)]
        trial = forecast_stock(
            stock_node(stock=opening, reserved_stock=reserve), demand, arrivals, 24, 6
        )
        assert trial.final_physical_stock == pytest.approx(
            opening + trial.delivered_quantity - trial.consumed_quantity
        )
        assert trial.consumed_quantity + trial.shortage_quantity == pytest.approx(demand)
        assert trial.final_physical_stock >= reserve
        assert all(value >= 0 for value in trial.usable_stock)
        assert trial.shortage_quantity >= 0


def test_demand_and_arrival_delay_monotonic_shortage_and_minimum() -> None:
    node = stock_node(stock=10)
    baseline = forecast_stock(node, 24, [(8, 10)], 30, 6)
    higher_demand = forecast_stock(node, 48, [(8, 10)], 30, 6)
    delayed = forecast_stock(node, 24, [(15, 10)], 30, 6)
    assert higher_demand.minimum_stock <= baseline.minimum_stock
    assert delayed.minimum_stock <= baseline.minimum_stock
    assert higher_demand.shortage_quantity >= baseline.shortage_quantity
    assert delayed.shortage_quantity >= baseline.shortage_quantity
    assert higher_demand.critical_hour is not None
    assert baseline.critical_hour is not None
    assert higher_demand.critical_hour <= baseline.critical_hour


def test_reporting_step_does_not_change_continuous_accounting() -> None:
    node = stock_node(stock=4, reserved_stock=1)
    first = forecast_stock(node, 24, [(3.1, 10), (15.5, 5)], 24, 1)
    second = forecast_stock(node, 24, [(3.1, 10), (15.5, 5)], 24, 24)
    for field in (
        "minimum_stock",
        "shortage_quantity",
        "critical_hour",
        "stockout_hour",
        "consumed_quantity",
        "delivered_quantity",
        "final_physical_stock",
    ):
        assert getattr(first, field) == pytest.approx(getattr(second, field))


def test_time_grid_includes_partial_last_interval() -> None:
    assert time_grid(13, 6) == (0, 6, 12, 13)
    assert time_grid(0.5, 6) == (0, 0.5)
    with pytest.raises(ValueError):
        time_grid(0, 1)


def test_readiness_exact_factors_and_threshold_timeline() -> None:
    resource = Resource(id="resource", capacity=100, load=50, operating_hours=2, rest_hours=3)
    path = route().model_copy(update={"environment_stress": 0.2, "altitude_stress": 0.3})
    result = evaluate_readiness(resource, path, 10, ReadinessConfig(), 6)
    assert result.factor_contributions == pytest.approx(
        {
            "base_readiness": 100,
            "load": -10,
            "duration": -5,
            "workload": -2.4,
            "rest": 3,
            "environment": -3,
            "altitude": -3,
            "clamping": 0,
        }
    )
    assert result.score == pytest.approx(79.6)
    assert result.state == "AMBER"
    assert result.feasible
    assert result.time_to_threshold_hours is None
    assert [point.hour for point in result.timeline] == [0, 6, 10]
    assert result.timeline[-1].score == result.score


def test_readiness_equality_feasible_and_below_boundary_infeasible() -> None:
    resource = Resource(id="resource", capacity=100, load=0, base_readiness=50)
    config = ReadinessConfig(duration_penalty_per_hour=1, workload_penalty_per_hour=0)
    boundary = evaluate_readiness(resource, route(), 10, config, 6)
    below = evaluate_readiness(resource, route(), 11, config, 6)
    assert boundary.score == 40
    assert boundary.feasible
    assert boundary.time_to_threshold_hours is None
    assert below.score == 39
    assert not below.feasible
    assert below.time_to_threshold_hours == 10
    assert 10 in [point.hour for point in below.timeline]


def test_readiness_load_rest_environment_duration_monotonicity() -> None:
    resource = Resource(id="resource", capacity=100, load=40, rest_hours=3)
    config = ReadinessConfig()
    path = route()
    base = readiness_score(resource, path, 10, config)
    assert readiness_score(resource.model_copy(update={"load": 80}), path, 10, config) < base
    assert readiness_score(resource.model_copy(update={"rest_hours": 5}), path, 10, config) > base
    assert readiness_score(resource, path, 20, config) < base
    assert (
        readiness_score(resource, path.model_copy(update={"environment_stress": 1}), 10, config)
        < base
    )
    overloaded = resource.model_copy(update={"load": 101, "rest_hours": 10})
    assert not evaluate_readiness(overloaded, path, 0, config, 6).feasible


def test_readiness_initial_failure_constant_score_and_rest_cap() -> None:
    resource = Resource(id="resource", capacity=100, load=0, base_readiness=10)
    config = ReadinessConfig(duration_penalty_per_hour=0, workload_penalty_per_hour=0)
    result = evaluate_readiness(resource, route(), 10, config, 6)
    assert result.score == 10
    assert result.time_to_threshold_hours == 0
    rested = resource.model_copy(update={"rest_hours": 100})
    assert evaluate_readiness(rested, route(), 10, config, 6).factor_contributions["rest"] == 10


def test_actual_sample_percentiles_are_interpolated_and_ordered() -> None:
    result = summarize([40, 0, 10, 20, 30])
    assert result.model_dump() == {"median": 20, "p10": 4, "p90": 36}
    assert summarize([7]).model_dump() == {"median": 7, "p10": 7, "p90": 7}
    with pytest.raises(ValueError):
        summarize([])
    with pytest.raises(ValueError):
        percentile([1], 1.1)


@pytest.mark.parametrize("daily,arrivals", [(-1, []), (24, [(-1, 10)]), (24, [(1, -1)])])
def test_supply_rejects_negative_arguments(
    daily: float, arrivals: list[tuple[float, float]]
) -> None:
    with pytest.raises(ValueError):
        forecast_stock(stock_node(), daily, arrivals, 10, 6)
