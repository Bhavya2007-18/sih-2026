"""Usable stock is physical stock minus a protected, fixed reserve.

Boundaries are inclusive: stock <= critical is critical; stock == 0 is stockout.
At simultaneous crossing/replenishment, record the pre-arrival crossing first.
Grid points are post-arrival; minima include both sides of every arrival.
Unmet demand accumulates and is never erased by a later delivery (no backlog).
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

from app.models import StockForecast, StockNode, StockPoint
from app.uncertainty.summarizer import summarize


@dataclass(frozen=True)
class StockTrial:
    hours: tuple[float, ...]
    usable_stock: tuple[float, ...]
    daily_consumption: float
    minimum_stock: float
    shortage_quantity: float
    critical_hour: float | None
    stockout_hour: float | None
    consumed_quantity: float
    delivered_quantity: float
    final_physical_stock: float


def time_grid(horizon_hours: float, step_hours: float) -> tuple[float, ...]:
    if horizon_hours <= 0 or step_hours <= 0:
        raise ValueError("horizon and step must be positive")
    return tuple(
        [index * step_hours for index in range(ceil(horizon_hours / step_hours))] + [horizon_hours]
    )


def forecast_stock(
    node: StockNode,
    daily_consumption: float,
    arrivals: Sequence[tuple[float, float]],
    horizon_hours: float,
    step_hours: float,
) -> StockTrial:
    """Integrate once between all actual arrivals and reporting grid points.

    Arrivals beyond the horizon are censored, never brought forward to a grid.
    Quantities and daily rates use abstract supply units, hours and units/day.
    """
    if daily_consumption < 0 or any(hour < 0 or quantity < 0 for hour, quantity in arrivals):
        raise ValueError("demand, arrival time and quantity must be nonnegative")
    hours = time_grid(horizon_hours, step_hours)
    deliveries: dict[float, float] = defaultdict(float)
    for hour, quantity in arrivals:
        if hour <= horizon_hours:
            deliveries[hour] += quantity
    usable = float(node.stock - node.reserved_stock)
    minimum = usable
    critical = 0.0 if usable <= node.critical_threshold else None
    stockout = 0.0 if usable == 0 else None
    rate = daily_consumption / 24.0
    consumed = 0.0
    unmet = 0.0
    delivered = 0.0
    previous = 0.0
    points: dict[float, float] = {}
    for hour in sorted(set(hours) | set(deliveries)):
        elapsed = hour - previous
        required = rate * elapsed
        if rate > 0:
            if critical is None and usable > node.critical_threshold:
                until_critical = (usable - node.critical_threshold) / rate
                if until_critical <= elapsed:
                    critical = previous + until_critical
            if stockout is None and usable / rate <= elapsed:
                stockout = previous + usable / rate
        taken = min(usable, required)
        consumed += taken
        unmet += required - taken
        usable = max(0.0, usable - taken)
        minimum = min(minimum, usable)
        arrival = deliveries.get(hour, 0.0)
        delivered += arrival
        usable += arrival
        if hour in hours:
            points[hour] = usable
        previous = hour
    return StockTrial(
        hours=hours,
        usable_stock=tuple(points[hour] for hour in hours),
        daily_consumption=daily_consumption,
        minimum_stock=minimum,
        shortage_quantity=unmet,
        critical_hour=critical,
        stockout_hour=stockout,
        consumed_quantity=consumed,
        delivered_quantity=delivered,
        final_physical_stock=usable + node.reserved_stock,
    )


def iso_date(start_time: str, hour: float | None) -> str | None:
    if hour is None:
        return None
    start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    return (start + timedelta(hours=hour)).isoformat()


def summarize_forecast(
    node: StockNode, trials: Sequence[StockTrial], start_time: str
) -> StockForecast:
    """Crossing-time percentiles are conditional on observing a crossing by horizon."""
    if not trials:
        raise ValueError("a forecast requires at least one trial")
    critical_times = [trial.critical_hour for trial in trials if trial.critical_hour is not None]
    stockout_times = [trial.stockout_hour for trial in trials if trial.stockout_hour is not None]
    critical = summarize(critical_times) if critical_times else None
    stockout = summarize(stockout_times) if stockout_times else None
    timeline = []
    for index, hour in enumerate(trials[0].hours):
        days = [
            trial.usable_stock[index] / trial.daily_consumption
            for trial in trials
            if trial.daily_consumption > 0
        ]
        timeline.append(
            StockPoint(
                hour=hour,
                stock=summarize([trial.usable_stock[index] for trial in trials]),
                days_of_supply=summarize(days) if days else None,
            )
        )
    return StockForecast(
        node_id=node.node_id,
        stock_timeline=timeline,
        minimum_stock=summarize([trial.minimum_stock for trial in trials]),
        shortage_quantity=summarize([trial.shortage_quantity for trial in trials]),
        time_to_critical_hours=critical,
        critical_probability=len(critical_times) / len(trials),
        critical_date=iso_date(start_time, critical.median if critical else None),
        time_to_stockout_hours=stockout,
        stockout_probability=len(stockout_times) / len(trials),
        stockout_date=iso_date(start_time, stockout.median if stockout else None),
        safety_threshold=node.safety_threshold,
        critical_threshold=node.critical_threshold,
        notes=[
            "Stock and threshold tests use nonnegative usable stock "
            "(physical minus fixed reserve).",
            "Critical means usable <= critical threshold; stockout means usable = 0, "
            "even at hour 0.",
            "Crossings/minima at an arrival are measured before replenishment; "
            "grid points after it.",
            "Shortage is cumulative unmet demand, not negative stock; "
            "later arrivals do not erase it.",
            "Critical/stockout bands and dates are conditional on a crossing within the horizon; "
            "non-crossing samples are censored, not assigned a fake crossing date.",
            "Days of supply is usable / sampled daily demand; null when demand is zero.",
            "P10/P90 are empirical simulation percentiles, not confidence intervals.",
        ],
    )
