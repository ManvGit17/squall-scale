"""squallscale controller: watch the fleet's load and scale it to fit.

A background thread scrapes each backend's /metrics, derives the recent
average latency, and asks the pure policy whether to add or remove a backend.
On a change it starts or drains a container and rewrites the load balancer's
upstream, reloading nginx without dropping requests. The current picture is
served as JSON on /state for the dashboard and the measured-run script.
"""
from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from statistics import fmean

import docker
import uvicorn
from fastapi import FastAPI

from config import Config
from fleet import Fleet
from scaling import Action, FleetState, decide
from scrape import Sample, recent_latency_ms, recent_throughput_rps

CFG = Config()
SCALING = CFG.scaling()


class Controller:
    def __init__(self) -> None:
        self.fleet = Fleet(docker.from_env(), CFG)
        self._prev: dict[str, tuple[Sample, float]] = {}
        self._last_up = 0.0
        self._last_down = 0.0
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._state: dict = {
            "fleet_size": 0, "signal_ms": None, "backends": [],
            "last_action": None, "history": [],
            "config": {
                "min_backends": SCALING.min_backends,
                "max_backends": SCALING.max_backends,
                "high_watermark_ms": SCALING.high_watermark_ms,
                "low_watermark_ms": SCALING.low_watermark_ms,
                "up_cooldown_s": SCALING.up_cooldown_s,
                "down_cooldown_s": SCALING.down_cooldown_s,
            },
        }

    # -- public state ------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            return {**self._state, "backends": list(self._state["backends"])}

    def _publish(self, **fields) -> None:
        with self._lock:
            self._state.update(fields)

    def _record_action(self, action: Action, reason: str, size: int) -> None:
        entry = {"action": action.value, "reason": reason,
                 "fleet_size": size, "at": time.time()}
        with self._lock:
            self._state["last_action"] = entry
            self._state["history"] = (self._state["history"] + [entry])[-50:]

    # -- loop --------------------------------------------------------------
    def bootstrap(self) -> None:
        self.fleet.adopt_counter()
        names = self.fleet.backend_names()
        while len(names) < SCALING.min_backends:
            names.append(self.fleet.create_backend())
        self.fleet.write_and_reload(names)
        self._last_up = self._last_down = time.monotonic()

    def run(self) -> None:
        self.bootstrap()
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:  # keep the loop alive; surface in state
                self._publish(error=f"{type(exc).__name__}: {exc}")
            self._stop.wait(CFG.interval_s)

    def _tick(self) -> None:
        now = time.monotonic()
        names = self.fleet.backend_names()
        backends_view = []
        latencies: list[float] = []
        total_in_flight = 0.0

        for name in names:
            cur = self.fleet.scrape(name)
            if cur is None:
                backends_view.append({"name": name, "healthy": False})
                continue
            total_in_flight += cur.in_flight
            lat = rps = None
            prev = self._prev.get(name)
            if prev is not None:
                lat = recent_latency_ms(prev[0], cur)
                rps = recent_throughput_rps(prev[0], cur, now - prev[1])
            self._prev[name] = (cur, now)
            if lat is not None:
                latencies.append(lat)
            backends_view.append({
                "name": name, "healthy": True,
                "in_flight": cur.in_flight,
                "recent_latency_ms": round(lat, 1) if lat is not None else None,
                "recent_rps": round(rps, 1) if rps is not None else None,
                "requests_total": cur.requests_total,
                "uptime_s": round(cur.uptime, 1),
            })

        # Drop state for backends that are gone.
        self._prev = {n: v for n, v in self._prev.items() if n in names}

        # Signal = recent average latency. With no completions this interval,
        # a fleet with nothing in flight is idle (treat as cold, 0ms); one with
        # requests still in flight is busy but unmeasured, so hold (None).
        if latencies:
            signal = round(fmean(latencies), 1)
        elif total_in_flight == 0:
            signal = 0.0
        else:
            signal = None
        state = FleetState(
            backends=len(names), signal_ms=signal,
            seconds_since_up=now - self._last_up,
            seconds_since_down=now - self._last_down,
        )
        action = decide(state, SCALING)

        self._publish(fleet_size=len(names), signal_ms=signal,
                      backends=backends_view, error=None)

        if action is Action.UP:
            new = self.fleet.create_backend()
            names.append(new)
            self.fleet.write_and_reload(names)
            self._last_up = time.monotonic()
            self._record_action(action, f"latency {signal}ms >= "
                                 f"{SCALING.high_watermark_ms}ms", len(names))
        elif action is Action.DOWN:
            victim = self._pick_victim(names)
            names.remove(victim)
            self.fleet.write_and_reload(names)      # stop routing to it
            time.sleep(CFG.drain_s)                  # let in-flight finish
            self.fleet.remove_backend(victim)
            self._last_down = time.monotonic()
            self._record_action(action, f"latency {signal}ms <= "
                                 f"{SCALING.low_watermark_ms}ms", len(names))

    @staticmethod
    def _pick_victim(names: list[str]) -> str:
        """Remove the most recently added backend (highest index)."""
        def idx(n: str) -> int:
            tail = n.rsplit("-", 1)[-1]
            return int(tail) if tail.isdigit() else 0
        return max(names, key=idx)

    def stop(self) -> None:
        self._stop.set()

    def cleanup(self) -> None:
        """Remove spawned backends so they don't outlive the controller."""
        try:
            self.fleet.remove_all()
        except Exception:
            pass


controller = Controller()


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=controller.run, daemon=True)
    thread.start()
    yield
    controller.stop()
    controller.cleanup()


app = FastAPI(title="squallscale controller", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/state")
def state() -> dict:
    return controller.snapshot()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=CFG.api_port, log_level="warning")
