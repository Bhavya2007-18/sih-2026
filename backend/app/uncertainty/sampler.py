"""Independent streams keyed by stable IDs, never Python's randomized hash()."""

import hashlib
import json
import random


def stream(seed: int, *keys: str | int) -> random.Random:
    """Same seed/keys give paired uniforms even when route order or inputs change."""
    payload = json.dumps([seed, *keys], separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest, "big"))


def sample_demand(seed: int, trial: int, node_id: str, daily: float, fraction: float) -> float:
    """One uniform daily rate per node/trial, held constant through the horizon."""
    u = stream(seed, "demand", node_id, trial).random()
    return daily * (1 + fraction * (2 * u - 1))
