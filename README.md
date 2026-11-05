# squallscale

**A self-hosted autoscaling platform you can watch breathe.**

A fleet of small C++ backends sits behind an nginx load balancer. A controller watches their load
and adds or removes backends as traffic rises and falls, the load-balancer upstream is rewritten
and reloaded live, and a dashboard animates requests flowing to each backend so you can watch the
fleet scale up and down in real time.

It grows from a tiny starting point — a raw C++ socket server, two replicas behind nginx, and a
Jenkins pipeline — which remain the repository's first commits.

> **Status.** Foundation milestone: the fleet runs under Docker Compose with one command, the
> backend reports its load and health, and continuous integration builds it and runs the tests.
> Elasticity (the autoscaler) and the live dashboard follow. See [`docs/roadmap.md`](docs/roadmap.md).

## Quick start

Requires Docker with the Compose plugin.

```bash
docker compose up --build
```

Then send it some traffic:

```bash
curl http://localhost:8088/            # Served by backend: <container>
curl http://localhost:8088/healthz     # ok
curl http://localhost:8088/metrics     # Prometheus-format load metrics
```

Repeat the first request and the backend name alternates — the load balancer is spreading traffic
across the fleet.

## The backend

A dependency-light C++ HTTP server. It answers every application path with its hostname, and adds
what a platform needs to make scaling decisions:

| Endpoint | Purpose |
| :-- | :-- |
| `/` (and any app path) | Returns `Served by backend: <host>`. Does a tunable amount of simulated work (`WORK_MS`) so load is controllable. |
| `/healthz` | Liveness check: `ok`. |
| `/metrics` | Prometheus text: requests total, in-flight, cumulative latency, uptime. |

It handles requests from a thread pool, so concurrency — and therefore in-flight count and latency
— is real and measurable. It drains in-flight requests on shutdown rather than cutting them off.

| Variable | Default | Meaning |
| :-- | :-- | :-- |
| `PORT` | `8080` | Listen port. |
| `THREADS` | `8` | Worker threads. |
| `WORK_MS` | `0` | Simulated work per request, in milliseconds. |
| `MAX_QUEUE` | `1024` | Connections queued before shedding with `503`. |
| `DRAIN_TIMEOUT_MS` | `8000` | Grace to finish in-flight requests on stop. |

## Measured: the thread-pool gain

A single worker handles one request at a time, like the original blocking loop. Extra workers let
requests overlap. The benchmark records the difference; rerun it any time:

```bash
python3 bench/benchmark.py --work-ms 40 --concurrency 32 --duration 8 --workers 1 8 16
```

Results are written to [`bench/results/`](bench/results/).

## Tests and CI

```bash
docker build --target test backend     # compile and run the C++ unit tests
bash scripts/smoke.sh                   # end-to-end check against a running fleet
```

GitHub Actions runs the unit tests and an end-to-end smoke test on every push. A Jenkins pipeline
([`Jenkinsfile`](Jenkinsfile)) builds, deploys and smoke-tests the fleet as well.

## Ports

`8088` load balancer · `8089` controller (later) · `8090` dashboard (later). Backends are internal
to the Compose network.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
