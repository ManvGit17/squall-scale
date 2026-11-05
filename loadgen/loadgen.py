#!/usr/bin/env python3
"""Drive traffic at the load balancer with controllable concurrency.

Presets:
  steady  constant concurrency
  ramp    concurrency rising linearly from --start to --end
  spike   low, then a burst to --peak, then low again

Closed-loop: a pool of workers each send requests back to back; the number
currently active follows the preset's schedule, so "concurrency" is the number
of in-flight clients. Standard library only.

  python loadgen/loadgen.py steady --concurrency 32 --duration 30
  python loadgen/loadgen.py ramp --start 2 --end 80 --duration 60
  python loadgen/loadgen.py spike --base 4 --peak 80 --duration 45
"""
from __future__ import annotations

import argparse
import http.client
import threading
import time
from collections.abc import Callable
from urllib.parse import urlparse


class LoadRunner:
    def __init__(self, url: str, schedule: Callable[[float], int],
                 duration: float, max_workers: int):
        parsed = urlparse(url)
        self._host = parsed.hostname or "localhost"
        self._port = parsed.port or 80
        self._path = parsed.path or "/"
        self._schedule = schedule
        self._duration = duration
        self._max_workers = max(1, max_workers)
        self._start = 0.0
        self._stop = threading.Event()
        self._target = 0
        self._completed = 0
        self._errors = 0
        self._lock = threading.Lock()

    def _elapsed(self) -> float:
        return time.monotonic() - self._start

    def _worker(self, index: int) -> None:
        conn = http.client.HTTPConnection(self._host, self._port, timeout=10)
        while not self._stop.is_set():
            if index >= self._target:
                time.sleep(0.05)
                continue
            try:
                conn.request("GET", self._path)
                resp = conn.getresponse()
                resp.read()
                with self._lock:
                    if resp.status == 200:
                        self._completed += 1
                    else:
                        self._errors += 1
            except OSError:
                with self._lock:
                    self._errors += 1
                conn.close()
                conn = http.client.HTTPConnection(self._host, self._port, timeout=10)
        conn.close()

    def run(self) -> dict:
        self._start = time.monotonic()
        workers = [threading.Thread(target=self._worker, args=(i,), daemon=True)
                   for i in range(self._max_workers)]
        for w in workers:
            w.start()

        last_report = 0.0
        last_completed = 0
        while self._elapsed() < self._duration:
            self._target = max(0, min(self._max_workers,
                                      self._schedule(self._elapsed())))
            time.sleep(0.2)
            now = self._elapsed()
            if now - last_report >= 2.0:
                with self._lock:
                    done = self._completed
                rps = (done - last_completed) / (now - last_report)
                print(f"t={now:5.1f}s  concurrency={self._target:3d}  "
                      f"~{rps:6.1f} rps  completed={done}")
                last_report, last_completed = now, done

        self._stop.set()
        for w in workers:
            w.join(timeout=12)
        with self._lock:
            return {"completed": self._completed, "errors": self._errors,
                    "duration_s": round(self._elapsed(), 1)}


def steady_schedule(c: int) -> Callable[[float], int]:
    return lambda _t: c


def ramp_schedule(start: int, end: int, duration: float) -> Callable[[float], int]:
    def sched(t: float) -> int:
        frac = min(1.0, t / duration) if duration > 0 else 1.0
        return round(start + (end - start) * frac)
    return sched


def spike_schedule(base: int, peak: int, duration: float) -> Callable[[float], int]:
    def sched(t: float) -> int:
        if t < duration * 0.25 or t > duration * 0.75:
            return base
        return peak
    return sched


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:8088")
    sub = p.add_subparsers(dest="preset", required=True)

    s = sub.add_parser("steady")
    s.add_argument("--concurrency", type=int, default=32)
    s.add_argument("--duration", type=float, default=30)

    r = sub.add_parser("ramp")
    r.add_argument("--start", type=int, default=2)
    r.add_argument("--end", type=int, default=80)
    r.add_argument("--duration", type=float, default=60)

    k = sub.add_parser("spike")
    k.add_argument("--base", type=int, default=4)
    k.add_argument("--peak", type=int, default=80)
    k.add_argument("--duration", type=float, default=45)
    return p


def runner_from_args(args: argparse.Namespace) -> LoadRunner:
    if args.preset == "steady":
        return LoadRunner(args.url, steady_schedule(args.concurrency),
                          args.duration, args.concurrency)
    if args.preset == "ramp":
        return LoadRunner(args.url, ramp_schedule(args.start, args.end, args.duration),
                          args.duration, max(args.start, args.end))
    if args.preset == "spike":
        return LoadRunner(args.url, spike_schedule(args.base, args.peak, args.duration),
                          args.duration, max(args.base, args.peak))
    raise ValueError(args.preset)


def main() -> None:
    args = build_parser().parse_args()
    runner = runner_from_args(args)
    print(f"load: {args.preset} -> {args.url}")
    result = runner.run()
    print(f"done: {result['completed']} ok, {result['errors']} errors, "
          f"{result['duration_s']}s")


if __name__ == "__main__":
    main()
