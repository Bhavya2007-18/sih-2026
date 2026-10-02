"""Coupled simulation tests: no hard-coded forecast outputs in orchestration."""

from pathlib import Path

import pytest

from app.core.comparison import compare_runs
from app.core.events import apply_events
from app.core.simulation import run_simulation
from app.models import Event, Inbound, ReadinessConfig, Scenario, StockNode
from app.readiness.engine import resource_feasible
from app.routing.engine import sample_duration
from app.uncertainty.sampler import sample_demand
from app.uncertainty.summarizer import summarize


def demo() -> Scenario:
    path = Path(__file__).resolve().parents[2] / "data" / "demo_scenario.json"
    return Scenario.model_validate_json(path.read_text())


def deterministic() -> Scenario:
    scenario = demo()
    scenario.routes = scenario.routes[:1]
    for segment in scenario.routes[0].segments:
        segment.time_variation_fraction = 0
        segment.disruption_probability = 0
    scenario.stock_nodes[0].demand_variation_fraction = 0
    return scenario


def test_seeded_repeatability_and_no_mutation() -> None:
    scenario = demo()
    scenario.events = [Event(id="delay", type="ROUTE_DELAY", target="route-a", magnitude=5)]
    snapshot = scenario.model_dump_json()
    first = run_simulation(scenario, 40)
    second = run_simulation(scenario, 40)
    assert first.model_dump_json() == second.model_dump_json()
    assert scenario.model_dump_json() == snapshot
    first.options[0].supply_forecast[0].notes.append("output mutation")
    assert "output mutation" not in run_simulation(scenario, 40).options[0].supply_forecast[0].notes


def test_route_order_does_not_change_any_result_or_recommendation() -> None:
    scenario = demo()
    baseline = run_simulation(scenario, 25)
    scenario.routes.reverse()
    assert run_simulation(scenario, 25).model_dump() == baseline.model_dump()


def test_changed_seed_changes_actual_uncertainty_samples() -> None:
    scenario = demo()
    first = run_simulation(scenario, 40)
    scenario.seed += 1
    second = run_simulation(scenario, 40)
    assert first.route_results[0].eta_hours != second.route_results[0].eta_hours
    for option in second.options:
        eta = option.route.eta_hours
        if eta is not None:
            assert eta.p10 <= eta.median <= eta.p90
        else:
            assert option.route.success_probability == 0
        assert 0 <= option.route.success_probability <= 1
        for node in option.supply_forecast:
            assert 0 <= node.critical_probability <= 1
            assert node.minimum_stock.p10 <= node.minimum_stock.median <= node.minimum_stock.p90


def test_clone_id_is_excluded_from_random_streams() -> None:
    scenario = demo()
    original = run_simulation(scenario, 20)
    scenario.id = "clone"
    cloned = run_simulation(scenario, 20)
    assert cloned.options == original.options


def test_delay_uses_paired_additive_draws_and_propagates_to_readiness_and_stock() -> None:
    scenario = deterministic()
    baseline = run_simulation(scenario, 5)
    scenario.events = [Event(id="delay", type="ROUTE_DELAY", target="route-a", magnitude=20)]
    changed = run_simulation(scenario, 5)
    assert changed.route_results[0].eta_hours is not None
    assert baseline.route_results[0].eta_hours is not None
    assert (
        changed.route_results[0].eta_hours.median - baseline.route_results[0].eta_hours.median == 20
    )
    assert changed.readiness_results[0].score < baseline.readiness_results[0].score
    baseline_stock = baseline.supply_forecast[0]
    changed_stock = changed.supply_forecast[0]
    assert (
        changed_stock.stock_timeline[5].stock.median < baseline_stock.stock_timeline[5].stock.median
    )
    assert changed_stock.time_to_critical_hours is not None
    assert baseline_stock.time_to_critical_hours is not None
    assert (
        changed_stock.time_to_critical_hours.median < baseline_stock.time_to_critical_hours.median
    )


def test_baseline_what_if_pairing_preserves_untouched_route_and_node_demand() -> None:
    scenario = demo()
    baseline = run_simulation(scenario, 30)
    scenario.events = [Event(id="delay", type="ROUTE_DELAY", target="route-a", magnitude=5)]
    changed = run_simulation(scenario, 30)
    before_b = next(option for option in baseline.options if option.route.route_id == "route-b")
    after_b = next(option for option in changed.options if option.route.route_id == "route-b")
    assert before_b == after_b
    before_a = next(option for option in baseline.options if option.route.route_id == "route-a")
    after_a = next(option for option in changed.options if option.route.route_id == "route-a")
    assert before_a.route.eta_hours is not None and after_a.route.eta_hours is not None
    assert after_a.route.eta_hours.median == pytest.approx(before_a.route.eta_hours.median + 5)
    assert (
        before_a.supply_forecast[0].stock_timeline[:3]
        == after_a.supply_forecast[0].stock_timeline[:3]
    )


def test_closure_forces_another_candidate_and_changes_coupled_forecast() -> None:
    scenario = demo()
    baseline = run_simulation(scenario, 40)
    assert baseline.selected_route_id == "route-a"
    scenario.events = [Event(id="closure", type="ROUTE_UNAVAILABLE", target="route-a")]
    changed = run_simulation(scenario, 40)
    assert changed.selected_route_id == "route-b"
    assert changed.readiness_results[0].score < baseline.readiness_results[0].score
    closed = next(option for option in changed.options if option.route.route_id == "route-a")
    assert closed.route.eta_hours is None
    assert not closed.route.feasible
    assert closed.route.success_probability == 0
    assert changed.supply_forecast[0].shortage_quantity.median > (
        baseline.supply_forecast[0].shortage_quantity.median
    )


def test_all_routes_unavailable_returns_no_inbound_forecast() -> None:
    scenario = deterministic()
    scenario.events = [Event(id="closure", type="ROUTE_UNAVAILABLE", target="route-a")]
    result = run_simulation(scenario, 2)
    assert result.selected_route_id is None
    assert result.readiness_results == []
    assert not result.route_results[0].feasible
    assert result.route_results[0].eta_hours is None
    stock = result.supply_forecast[0]
    assert stock.shortage_quantity.median == 70
    assert stock.time_to_critical_hours is not None
    assert stock.time_to_critical_hours.median == 38
    assert stock.time_to_stockout_hours is not None
    assert stock.time_to_stockout_hours.median == 50
    assert stock.critical_date == "2026-10-03T14:00:00+00:00"


def test_inbound_total_not_each_individual_is_bounded_by_load() -> None:
    scenario = deterministic()
    scenario.stock_nodes[0].scheduled_inbound = [
        Inbound(id="first", quantity=40),
        Inbound(id="second", quantity=40),
    ]
    result = run_simulation(scenario, 1)
    assert result.selected_route_id is None
    assert result.supply_forecast[0].shortage_quantity.median == 70
    assert any("Aggregate inbound" in driver for driver in result.route_results[0].drivers)


@pytest.mark.parametrize("failure", ["resource_capacity", "route_capacity", "readiness", "horizon"])
def test_failed_constraints_deliver_no_supply(failure: str) -> None:
    scenario = deterministic()
    if failure == "resource_capacity":
        scenario.resources[0].load = 101
        scenario.routes[0].capacity = 200
    elif failure == "route_capacity":
        scenario.routes[0].capacity = 59
    elif failure == "readiness":
        scenario.resources[0].base_readiness = 10
    else:
        scenario.events = [Event(id="delay", type="ROUTE_DELAY", target="route-a", magnitude=121)]
    result = run_simulation(scenario, 3)
    assert result.selected_route_id is None
    assert result.route_results[0].success_probability == 0
    assert result.supply_forecast[0].shortage_quantity.median == 70


def test_resource_failure_in_one_group_cancels_all_deliveries() -> None:
    scenario = deterministic()
    first = scenario.resources[0]
    first.load = 30
    scenario.resources.append(first.model_copy(update={"id": "second", "base_readiness": 10}))
    result = run_simulation(scenario, 2)
    assert result.selected_route_id is None
    assert result.supply_forecast[0].shortage_quantity.median == 70


def test_actual_sample_readiness_controls_each_arrival_not_median_card() -> None:
    scenario = deterministic()
    scenario.horizon_hours = 40
    path = scenario.routes[0]
    path.environment_stress = path.altitude_stress = 0
    path.segments[0].nominal_hours = 20
    path.segments[0].time_variation_fraction = 1
    scenario.stock_nodes[0].stock = 0
    scenario.stock_nodes[0].daily_consumption = 0
    scenario.readiness_config = ReadinessConfig(
        load_penalty=0,
        duration_penalty_per_hour=2,
        workload_penalty_per_hour=0,
        rest_recovery_per_hour=0,
    )
    result = run_simulation(scenario, 80)
    durations = [sample_duration(path, scenario.seed, trial) for trial in range(80)]
    successful = [
        duration
        for duration in durations
        if resource_feasible(scenario.resources[0], path, duration, scenario.readiness_config)
    ]
    assert 0 < len(successful) < 80
    assert result.route_results[0].success_probability == len(successful) / 80
    assert result.route_results[0].eta_hours == summarize(successful)
    assert result.supply_forecast[0].stock_timeline[-1].stock == summarize(
        [60.0 if duration in successful else 0.0 for duration in durations]
    )
    assert result.supply_forecast[0].stock_timeline[-1].stock.p10 == 0
    assert result.supply_forecast[0].stock_timeline[-1].stock.p90 == 60


def test_one_demand_draw_per_trial_is_shared_by_all_routes() -> None:
    scenario = demo()
    for route in scenario.routes:
        for segment in route.segments:
            segment.available = False
    result = run_simulation(scenario, 20)
    assert all(option.supply_forecast == result.supply_forecast for option in result.options)
    node = scenario.stock_nodes[0]
    rates = [
        sample_demand(
            scenario.seed,
            trial,
            node.node_id,
            node.daily_consumption,
            node.demand_variation_fraction,
        )
        for trial in range(20)
    ]
    assert result.supply_forecast[0].shortage_quantity.model_dump() == pytest.approx(
        summarize([rate * 5 - node.stock for rate in rates]).model_dump()
    )


def test_departure_offset_and_horizon_are_respected() -> None:
    scenario = deterministic()
    scenario.horizon_hours = 30
    scenario.stock_nodes[0].daily_consumption = 0
    shipment = scenario.stock_nodes[0].scheduled_inbound[0]
    shipment.departure_hour = 6
    at_boundary = run_simulation(scenario, 1)
    assert at_boundary.supply_forecast[0].stock_timeline[-1].stock.median == 110
    shipment.departure_hour = 6.1
    too_late = run_simulation(scenario, 1)
    assert too_late.supply_forecast[0].stock_timeline[-1].stock.median == 50


def test_zero_demand_days_of_supply_null_and_no_fake_critical_date() -> None:
    scenario = deterministic()
    scenario.stock_nodes[0].daily_consumption = 0
    result = run_simulation(scenario, 2)
    stock = result.supply_forecast[0]
    assert stock.critical_probability == stock.stockout_probability == 0
    assert stock.critical_date is stock.stockout_date is None
    assert stock.time_to_critical_hours is stock.time_to_stockout_hours is None
    assert all(point.days_of_supply is None for point in stock.stock_timeline)


def test_custom_scoring_and_id_ties_are_transparent() -> None:
    scenario = demo()
    scenario.scoring.time_weight = 0
    scenario.scoring.failure_weight = 0
    scenario.scoring.critical_stock_weight = 0
    scenario.routes.reverse()
    result = run_simulation(scenario, 5)
    assert result.selected_route_id == "route-a"
    assert all(option.route.score == 0 for option in result.options)
    assert any("0 *" in driver for driver in result.route_results[0].drivers)
    assert any("Ranking cost" in item for item in result.assumptions)


def test_connectivity_events_do_not_change_physical_outputs_or_snapshot() -> None:
    scenario = deterministic()
    baseline = run_simulation(scenario, 5)
    scenario.events = [Event(id="offline", type="CONNECTIVITY_LOSS", target=scenario.id)]
    offline = run_simulation(scenario, 5)
    assert scenario.connectivity_online
    assert offline.data_resilience["connectivity_online"] is False
    assert offline.options == baseline.options
    scenario.events.append(Event(id="online", type="CONNECTIVITY_RESTORE", target=scenario.id))
    assert run_simulation(scenario, 5).data_resilience["connectivity_online"] is True


def test_absolute_at_start_event_semantics_and_input_order() -> None:
    scenario = deterministic()
    scenario.events = [
        Event(id="demand", type="DEMAND_CHANGE", target="lake", magnitude=48),
        Event(id="load", type="LOAD_CHANGE", target="transport-1", magnitude=70),
        Event(id="rest", type="REST_CHANGE", target="transport-1", magnitude=2),
        Event(id="environment", type="ENVIRONMENT_CHANGE", target="route-a", magnitude=0.7),
        Event(id="delay-1", type="ROUTE_DELAY", target="route-a", magnitude=2),
        Event(id="delay-2", type="ROUTE_DELAY", target="route-a", magnitude=3),
    ]
    applied = apply_events(scenario)
    assert applied.scenario.stock_nodes[0].daily_consumption == 48
    assert applied.scenario.resources[0].load == 70
    assert applied.scenario.resources[0].rest_hours == 2
    assert applied.scenario.routes[0].environment_stress == 0.7
    assert applied.route_delays == {"route-a": 5}
    assert scenario.stock_nodes[0].daily_consumption == 24
    assert scenario.resources[0].rest_hours == 8


def test_unsupported_future_event_is_explicitly_rejected() -> None:
    scenario = deterministic()
    scenario.events = [
        Event.model_construct(
            id="future", type="ROUTE_DELAY", target="route-a", magnitude=1, start_hour=4
        )
    ]
    with pytest.raises(ValueError, match="at-start"):
        run_simulation(scenario, 1)


@pytest.mark.parametrize("samples", [0, -1, 1001, True, 1.5])
def test_sample_workload_bound(samples: int) -> None:
    with pytest.raises(ValueError, match="samples"):
        run_simulation(demo(), samples)


def test_comparison_contract_delta_null_for_categories_and_missing_values() -> None:
    scenario = deterministic()
    baseline = run_simulation(scenario, 2)
    scenario.events = [
        Event(id="delay", type="ROUTE_DELAY", target="route-a", magnitude=20),
        Event(id="offline", type="CONNECTIVITY_LOSS", target=scenario.id),
    ]
    changed = run_simulation(scenario, 2)
    diff = compare_runs(baseline, changed)
    assert set(diff) == {"changes", "explanation"}
    changes = {item["metric"]: item for item in diff["changes"]}
    assert changes["eta_hours"]["delta"] == 20
    assert changes["readiness_score"]["delta"] == pytest.approx(-14)
    assert changes["connectivity_online"] == {
        "metric": "connectivity_online",
        "before": True,
        "after": False,
        "delta": None,
    }
    assert changes["route"]["delta"] is None
    assert all(isinstance(item, str) for item in diff["explanation"])
    scenario.events.append(Event(id="closure", type="ROUTE_UNAVAILABLE", target="route-a"))
    unavailable = compare_runs(baseline, run_simulation(scenario, 2))
    no_route = {item["metric"]: item for item in unavailable["changes"]}
    assert no_route["eta_hours"]["after"] is None
    assert no_route["eta_hours"]["delta"] is None
    assert no_route["readiness_score"]["after"] is None


def test_comparison_uses_destination_and_lowest_resource_readiness() -> None:
    scenario = deterministic()
    scenario.stock_nodes.insert(
        0,
        StockNode(
            node_id="cedar",
            stock=1000,
            daily_consumption=0,
            safety_threshold=10,
            critical_threshold=5,
        ),
    )
    result = run_simulation(scenario, 2)
    result.readiness_results.append(
        result.readiness_results[0].model_copy(update={"resource_id": "second", "score": 41})
    )
    changes = {item["metric"]: item for item in compare_runs(result, result)["changes"]}
    assert changes["minimum_stock"]["before"] == 0
    assert changes["readiness_score"]["before"] == 41
    assert changes["minimum_stock"]["delta"] == 0
    assert "No change" in compare_runs(result, result)["explanation"][0]


def test_comparison_discloses_unpaired_samples_and_conditional_critical_times() -> None:
    scenario = deterministic()
    baseline = run_simulation(scenario, 2)
    scenario.seed += 1
    changed = run_simulation(scenario, 3)
    diff = compare_runs(baseline, changed)
    assert any("not fully paired" in line for line in diff["explanation"])
    assert any("condition on" in line for line in diff["explanation"])


def test_segment_delay_and_travel_uniform_are_explicit_independent_draws() -> None:
    path = deterministic().routes[0]
    path.segments[0].time_variation_fraction = 0.5
    without_delay = [sample_duration(path, 42, index) for index in range(20)]
    assert all(12 <= duration <= 36 for duration in without_delay)
    path.segments[0].disruption_probability = 1
    path.segments[0].disruption_delay_hours = 7
    with_delay = [sample_duration(path, 42, index) for index in range(20)]
    assert with_delay == pytest.approx([duration + 7 for duration in without_delay])
    path.segments[0].disruption_probability = 0
    assert [sample_duration(path, 42, index) for index in range(20)] == without_delay


def test_all_inbound_is_delivered_at_exact_load_and_route_capacity_boundary() -> None:
    scenario = deterministic()
    scenario.routes[0].capacity = 60
    scenario.resources[0].capacity = 60
    scenario.stock_nodes[0].scheduled_inbound = [
        Inbound(id="first", quantity=20),
        Inbound(id="second", quantity=40),
    ]
    result = run_simulation(scenario, 1)
    assert result.selected_route_id == "route-a"
    assert result.route_results[0].success_probability == 1
    assert result.supply_forecast[0].stock_timeline[4].stock.median == 86


def test_at_start_environment_rest_and_load_changes_reach_readiness() -> None:
    scenario = deterministic()
    original = run_simulation(scenario, 1)
    scenario.events = [
        Event(id="environment", type="ENVIRONMENT_CHANGE", target="route-a", magnitude=1),
        Event(id="rest", type="REST_CHANGE", target="transport-1", magnitude=0),
        Event(id="load", type="LOAD_CHANGE", target="transport-1", magnitude=90),
    ]
    changed = run_simulation(scenario, 1)
    assert changed.readiness_results[0].score < original.readiness_results[0].score
    factors = changed.readiness_results[0].factor_contributions
    assert factors["environment"] == -15
    assert factors["rest"] == 0
    assert factors["load"] == -18


def test_demand_event_higher_rate_propagates_earlier_critical_and_more_shortage() -> None:
    scenario = deterministic()
    original = run_simulation(scenario, 1).supply_forecast[0]
    scenario.events = [Event(id="demand", type="DEMAND_CHANGE", target="lake", magnitude=48)]
    changed = run_simulation(scenario, 1).supply_forecast[0]
    assert changed.time_to_critical_hours is not None
    assert original.time_to_critical_hours is not None
    assert changed.time_to_critical_hours.median < original.time_to_critical_hours.median
    assert changed.shortage_quantity.median > original.shortage_quantity.median


def test_public_simulation_entrypoints_include_comparison() -> None:
    from app.core.simulation import compare_runs as public_comparison

    result = run_simulation(deterministic(), 1)
    assert public_comparison(result, result) == compare_runs(result, result)
