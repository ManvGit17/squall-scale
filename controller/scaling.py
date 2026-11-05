"""The autoscaling decision — a pure function, unit-tested without Docker.

The signal is the recent average request latency across healthy backends,
computed by the controller from successive metric scrapes. Latency rises when
the fleet is saturated and falls once there is enough capacity, so it makes a
clear, non-saturating scaling signal.

Separate cooldowns for scaling up and down stop the fleet from flapping, and
hard minimum and maximum bounds keep it sane.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(str, Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass(frozen=True)
class ScalingConfig:
    min_backends: int = 2
    max_backends: int = 6
    # Scaling signal: recent average latency per backend, in milliseconds.
    high_watermark_ms: float = 150.0
    low_watermark_ms: float = 70.0
    up_cooldown_s: float = 10.0
    down_cooldown_s: float = 25.0


@dataclass(frozen=True)
class FleetState:
    backends: int
    signal_ms: float | None  # None until two scrapes give a recent latency
    seconds_since_up: float
    seconds_since_down: float


def decide(state: FleetState, cfg: ScalingConfig) -> Action:
    """Decide whether to add a backend, remove one, or hold.

    Bounds win first: below the minimum we always grow, above the maximum we
    always shrink. Otherwise the watermark must be breached *and* the matching
    cooldown elapsed.
    """
    if state.backends < cfg.min_backends:
        return Action.UP
    if state.backends > cfg.max_backends:
        return Action.DOWN

    # No signal yet (first tick): hold.
    if state.signal_ms is None:
        return Action.NONE

    if (state.signal_ms >= cfg.high_watermark_ms
            and state.backends < cfg.max_backends
            and state.seconds_since_up >= cfg.up_cooldown_s):
        return Action.UP

    if (state.signal_ms <= cfg.low_watermark_ms
            and state.backends > cfg.min_backends
            and state.seconds_since_down >= cfg.down_cooldown_s):
        return Action.DOWN

    return Action.NONE
