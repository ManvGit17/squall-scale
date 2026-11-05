"""Parse the backend's Prometheus /metrics and derive recent latency.

Pure functions: the control loop fetches the text over HTTP, but parsing and
the latency delta are tested without any network.
"""
from __future__ import annotations

from dataclasses import dataclass


def parse_prometheus(text: str) -> dict[str, float]:
    """Parse simple (unlabelled) Prometheus samples into {name: value}.

    Comment lines (``# HELP`` / ``# TYPE``) are ignored, as are labelled
    series such as ``..._info{host="x"} 1`` — the backend's scaling metrics
    are all unlabelled.
    """
    out: dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, value = line.rpartition(" ")
        if not name or "{" in name:  # skip labelled series
            continue
        try:
            out[name] = float(value)
        except ValueError:
            continue
    return out


def parse_host(text: str) -> str | None:
    """Pull the host label out of ``squallscale_backend_info{host="..."}``."""
    marker = 'squallscale_backend_info{host="'
    start = text.find(marker)
    if start == -1:
        return None
    start += len(marker)
    end = text.find('"', start)
    return text[start:end] if end != -1 else None


@dataclass(frozen=True)
class Sample:
    requests_total: float = 0.0
    in_flight: float = 0.0
    duration_sum: float = 0.0
    duration_count: float = 0.0
    uptime: float = 0.0

    @classmethod
    def from_text(cls, text: str) -> "Sample":
        m = parse_prometheus(text)
        return cls(
            requests_total=m.get("squallscale_requests_total", 0.0),
            in_flight=m.get("squallscale_requests_in_flight", 0.0),
            duration_sum=m.get("squallscale_request_duration_seconds_sum", 0.0),
            duration_count=m.get("squallscale_request_duration_seconds_count", 0.0),
            uptime=m.get("squallscale_uptime_seconds", 0.0),
        )


def recent_latency_ms(prev: Sample, cur: Sample) -> float | None:
    """Average latency (ms) of requests completed between two samples.

    Returns None when no requests completed in the interval, so an idle
    backend does not report a misleading zero.
    """
    dcount = cur.duration_count - prev.duration_count
    if dcount <= 0:
        return None
    dsum = cur.duration_sum - prev.duration_sum
    return (dsum / dcount) * 1000.0


def recent_throughput_rps(prev: Sample, cur: Sample, dt_s: float) -> float:
    """Requests completed per second between two samples."""
    if dt_s <= 0:
        return 0.0
    return max(0.0, (cur.duration_count - prev.duration_count) / dt_s)
