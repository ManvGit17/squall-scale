# Architecture

squallscale is four small pieces around a shared Docker network. One `docker compose up` builds the
backend image, starts the load balancer, the controller and the dashboard, and the controller then
runs the fleet.

```
                 load generator  (steady / spike / ramp)
                        |
                        v
      host :8088 +----------------+
                 |     nginx      |  upstream rewritten + hot-reloaded live
                 | load balancer  |  as the fleet changes; X-Backend header
                 +----------------+
                   |     |     |
            +------+     |     +------+
            v            v            v
       +---------+  +---------+  +---------+
       | backend |  | backend |  | backend |   C++ thread-pool servers
       |  :8080  |  |  :8080  |  |  :8080  |   /healthz  /metrics
       +---------+  +---------+  +---------+
            ^            ^            ^
            |   scrape /metrics (latency, in-flight, totals)
            +------------+------------+
                         |
                         v
      host :8089 +------------------+  docker API: start / drain backends
                 |    controller    |  decide scale up/down (watermarks,
                 | (FastAPI + loop) |  cooldowns); rewrite nginx upstream
                 +------------------+  serve /state
                         |  poll /state
                         v
      host :8090 +------------------+
                 |    dashboard     |  animate the fleet; chart latency vs
                 |  (React + SVG)   |  fleet size; live or recorded replay
                 +------------------+
```

## The backend (`backend/`)

A dependency-light C++17 HTTP server. The accept loop hands each connection to a fixed thread pool,
so concurrency is real and the queue builds under load. It serves any application path with its
hostname, answers `/healthz`, and exposes Prometheus metrics on `/metrics`: requests served,
in-flight, cumulative latency and uptime. Latency is measured **from acceptance**, so it includes
queue wait — the signal that reveals saturation. A `WORK_MS` knob adds controllable simulated work.
On `SIGTERM` it stops accepting and drains in-flight requests before exiting.

Pure logic (request parsing, metrics rendering) is split into headers and unit-tested without
sockets.

## The load balancer (`nginx/`)

Stock nginx, pinned to a single worker so round-robin is deterministic at this scale. The controller
owns its upstream config: on every fleet change it writes a new `default.conf` into a shared volume
and triggers `nginx -s reload`, which swaps config without dropping connections. Passive health
checks (`max_fails`/`fail_timeout`) step over a backend that errors.

## The controller (`controller/`)

A FastAPI app with a background control loop. Each tick it scrapes every backend, derives the recent
average latency, and asks a **pure decision function** ([`scaling.py`](../controller/scaling.py))
whether to grow, shrink or hold — bounded by min/max and paced by separate up/down cooldowns.
Scale-up is health-gated; scale-down drains the backend out of nginx before stopping it. It talks to
Docker through the mounted socket and publishes the live picture on `/state`.

The layering keeps the testable parts pure: `scaling.py` (policy), `scrape.py` (metrics parsing) and
`nginx_conf.py` (config rendering) have no Docker or network dependency; `fleet.py` and `app.py` are
the side-effecting shell.

## The dashboard (`dashboard/`)

A React + TypeScript single-page app. In **live** mode it polls the controller's `/state`; in
**replay** mode it plays a recorded run bundled as `replay.json`, so the demo works with no backend
(for example on a static host). It auto-detects which to use. The chart is hand-drawn SVG; backend
cards animate in and out and pulse at a rate set by their throughput.

## CI/CD

GitHub Actions builds and tests on every push (C++ unit tests, controller unit tests, the dashboard
build and test, and an end-to-end fleet smoke). The Jenkins pipeline builds and smoke-tests the
fleet too ([`Jenkinsfile`](../Jenkinsfile)).
