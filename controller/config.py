"""Controller configuration, from environment variables with sane defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass

from scaling import ScalingConfig


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    # Fleet / Docker
    backend_image: str = os.environ.get("BACKEND_IMAGE", "squallscale-backend:local")
    network: str = os.environ.get("NETWORK", "squallscale")
    lb_container: str = os.environ.get("LB_CONTAINER", "squallscale-lb")
    backend_label: str = "squallscale.role"
    backend_port: int = _int("BACKEND_PORT", 8080)
    backend_work_ms: int = _int("WORK_MS", 40)
    backend_threads: int = _int("THREADS", 8)

    # nginx config the controller writes (shared volume with the lb).
    nginx_conf_path: str = os.environ.get("NGINX_CONF_PATH", "/nginx-conf/default.conf")

    # Control loop
    interval_s: float = _float("INTERVAL_S", 2.0)
    drain_s: float = _float("DRAIN_S", 5.0)
    health_timeout_s: float = _float("HEALTH_TIMEOUT_S", 20.0)

    # API
    api_port: int = _int("API_PORT", 8089)

    def scaling(self) -> ScalingConfig:
        return ScalingConfig(
            min_backends=_int("MIN_BACKENDS", 2),
            max_backends=_int("MAX_BACKENDS", 6),
            high_watermark_ms=_float("HIGH_WATERMARK_MS", 150.0),
            low_watermark_ms=_float("LOW_WATERMARK_MS", 70.0),
            up_cooldown_s=_float("UP_COOLDOWN_S", 10.0),
            down_cooldown_s=_float("DOWN_COOLDOWN_S", 25.0),
        )
