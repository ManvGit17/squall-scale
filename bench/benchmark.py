#!/usr/bin/env python3
"""Measure the throughput gain from the backend's thread pool.

For each worker count, run one backend container, drive it with a fixed number
of concurrent clients in a closed loop, and record completed requests per
second and latency percentiles. A single worker is the serialized baseline:
it behaves like the original blocking accept loop, handling one request at a
time. More workers let requests overlap, so throughput should climb.

Only the Python standard library and the `docker` CLI are used.

    python3 bench/benchmark.py --work-ms 40 --concurrency 32 --duration 8 \
        --workers 1 8 16

Results are written to bench/results/ as JSON and Markdown and printed.
"""
from __future__ import annotations

import argparse
import http.client
import json
import pathlib
import statistics
import subprocess
import threading
import time
from datetime import datetime, timezone

RESULTS_DIR = pathlib.Path(__file__).resolve().parent / "results"
IMAGE = "squallscale-backend:local"
CONTAINER = "squallscale-bench"


def run(cmd: list[str], check: bool = True, capture: bool = False) -> str:
    result = subprocess.run(
        cmd, check=check, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    return result.stdout or ""


def build_image() -> None:
    backend = pathlib.Path(__file__).resolve().parent.parent / "backend"
    run(["docker", "build", "-t", IMAGE, str(backend)])


def start_backend(port: int, workers: int, work_ms: int) -> None:
    run(["docker", "rm", "-f", CONTAINER], check=False, capture=True)
    run([
        "docker", "run", "-d", "--name", CONTAINER,
        "-p", f"{port}:8080",
        "-e", f"THREADS={workers}",
        "-e", f"WORK_MS={work_ms}",
        IMAGE,
    ])


def stop_backend() -> None:
    run(["docker", "rm", "-f", CONTAINER], check=False, capture=True)


def wait_ready(port: int, timeout_s: int = 30) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("GET", "/healthz")
            if conn.getresponse().status == 200:
                conn.close()
                return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"backend on port {port} never became ready")


def load_worker(port: int, stop_at: float, latencies: list[float],
                counters: list[int], index: int) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    local: list[float] = []
    done = 0
    while time.time() < stop_at:
        t0 = time.perf_counter()
        try:
            conn.request("GET", "/")
            resp = conn.getresponse()
            resp.read()
            if resp.status == 200:
                local.append((time.perf_counter() - t0) * 1000.0)
                done += 1
            else:
                conn.close()
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        except OSError:
            conn.close()
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.close()
    latencies.extend(local)
    counters[index] = done


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(round(pct / 100.0 * (len(ordered) - 1)))))
    return ordered[k]


def measure(port: int, concurrency: int, duration: int) -> dict:
    latencies: list[float] = []
    counters = [0] * concurrency
    stop_at = time.time() + duration
    threads = [
        threading.Thread(target=load_worker,
                         args=(port, stop_at, latencies, counters, i))
        for i in range(concurrency)
    ]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    total = sum(counters)
    return {
        "requests": total,
        "elapsed_s": round(elapsed, 3),
        "throughput_rps": round(total / elapsed, 1) if elapsed else 0.0,
        "latency_ms_p50": round(percentile(latencies, 50), 1),
        "latency_ms_p95": round(percentile(latencies, 95), 1),
        "latency_ms_p99": round(percentile(latencies, 99), 1),
        "latency_ms_mean": round(statistics.fmean(latencies), 1) if latencies else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-ms", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--duration", type=int, default=8)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 8, 16])
    parser.add_argument("--port", type=int, default=8095)
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()

    if not args.no_build:
        build_image()

    rows = []
    try:
        for workers in args.workers:
            start_backend(args.port, workers, args.work_ms)
            try:
                wait_ready(args.port)
                # Warm up briefly so the first run isn't penalised.
                measure(args.port, args.concurrency, 1)
                result = measure(args.port, args.concurrency, args.duration)
            finally:
                stop_backend()
            result["workers"] = workers
            rows.append(result)
            print(f"workers={workers:>3}  "
                  f"{result['throughput_rps']:>8.1f} rps  "
                  f"p50={result['latency_ms_p50']:>6.1f}ms  "
                  f"p95={result['latency_ms_p95']:>6.1f}ms")
    finally:
        stop_backend()

    baseline = next((r["throughput_rps"] for r in rows if r["workers"] == 1), None)
    for r in rows:
        r["speedup_vs_1_worker"] = (
            round(r["throughput_rps"] / baseline, 2) if baseline else None
        )

    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {
            "work_ms": args.work_ms,
            "concurrency": args.concurrency,
            "duration_s": args.duration,
        },
        "runs": rows,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "throughput.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md = ["# Thread-pool throughput", "",
          f"Generated {report['generated_utc']}.", "",
          f"Each run: {args.concurrency} concurrent clients, closed loop, "
          f"{args.duration}s, {args.work_ms}ms simulated work per request.",
          "",
          "| Workers | Throughput (rps) | p50 (ms) | p95 (ms) | p99 (ms) | Speedup vs 1 |",
          "| ------: | ---------------: | -------: | -------: | -------: | -----------: |"]
    for r in rows:
        md.append(
            f"| {r['workers']} | {r['throughput_rps']} | {r['latency_ms_p50']} | "
            f"{r['latency_ms_p95']} | {r['latency_ms_p99']} | "
            f"{r['speedup_vs_1_worker']}x |")
    md += ["",
           "One worker is the serialized baseline: it handles a single request "
           "at a time, like the original blocking accept loop. With simulated "
           "per-request work, extra workers let requests overlap, so throughput "
           "rises roughly with the worker count until the host runs out of room.",
           ""]
    (RESULTS_DIR / "throughput.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\nwrote {RESULTS_DIR / 'throughput.json'}")
    print(f"wrote {RESULTS_DIR / 'throughput.md'}")


if __name__ == "__main__":
    main()
