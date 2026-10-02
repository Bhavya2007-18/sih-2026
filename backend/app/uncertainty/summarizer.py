"""Empirical linear-interpolated percentiles, not statistical confidence bounds."""

from collections.abc import Sequence
from math import floor

from app.models import Summary


def percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot summarize an empty sample")
    if not 0 <= probability <= 1:
        raise ValueError("percentile probability must be in [0, 1]")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(values: Sequence[float]) -> Summary:
    return Summary(
        median=percentile(values, 0.5),
        p10=percentile(values, 0.1),
        p90=percentile(values, 0.9),
    )
