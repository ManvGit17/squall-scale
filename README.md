# squallscale

**A self-hosted autoscaling platform you can watch breathe.**

A fleet of small C++ backends sits behind an nginx load balancer. A controller watches their load
and adds or removes backends as traffic rises and falls, the load-balancer upstream is rewritten
and reloaded live, and a dashboard animates requests flowing to each backend so you can watch the
fleet scale up and down in real time.

It grows from a tiny starting point — a raw C++ socket server, two replicas behind nginx, and a
Jenkins pipeline — which remain the repository's first commits.

> **Status.** Elasticity milestone: the fleet runs with one command, the backend reports its load
> and health, and a controller scales the backend set up and down to match traffic — rewriting the
> load balancer live, with no dropped requests. The live dashboard follows. See
> [`docs/roadmap.md`](docs/roadmap.md) and [`docs/elasticity.md`](docs/elasticity.md).

## Quick start

Requires Docker with the Compose plugin.

```bash
docker compose up --build
```

This starts the load balancer and the controller; the controller then starts the backends and
keeps managing them. Send it some traffic:

```bash
curl http://localhost:8088/            # Served by backend: <container>
curl http://localhost:8088/healthz     # ok
curl http://localhost:8088/metrics     # Prometheus-format load metrics
curl http://localhost:8089/state       # the controller's live view of the fleet
```

Repeat the first request and the backend name changes — the load balancer is spreading traffic
across the fleet. Tear everything down (including backends the controller spawned) with:

```bash
bash scripts/down.sh
```

## Watch it scale

Drive traffic with the load generator and watch the fleet grow and shrink in the controller's
`/state`:

```bash
python loadgen/loadgen.py ramp --start 2 --end 100 --duration 60
python loadgen/loadgen.py spike --base 4 --peak 80 --duration 45
python loadgen/loadgen.py steady --concurrency 32 --duration 30
```

Or run the measured end-to-end scale cycle, which records a CSV, a chart and a summary:

```bash
python scripts/scale_run.py
```

See [`docs/elasticity.md`](docs/elasticity.md) for how the autoscaler decides and a recorded run
with real numbers.

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

`8088` load balancer · `8089` controller API · `8090` dashboard (later). Backends are internal to
the Compose network.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
