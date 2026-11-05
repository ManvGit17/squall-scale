# squallscale — roadmap

**squallscale** is a small, self-hosted autoscaling platform you can watch breathe. A fleet of
tiny C++ backends sits behind an nginx load balancer; a controller watches their load and adds or
removes backends as traffic rises and falls; the load-balancer upstream is rewritten and reloaded
live; and a dashboard animates requests flowing to each backend so the fleet visibly scales up and
down in real time.

It grows directly out of a five-file starting point — a raw C++ socket server, two replicas behind
nginx, and a Jenkins pipeline — which are the repository's first commits, so the foundation stays
visible in the history.

## Architecture

```
                 load generator
              (steady / spike / ramp)
                        |
                        v
                +----------------+
      host :8088 |     nginx      |   upstream rewritten + reloaded live,
                 | load balancer  |   unhealthy backends dropped
                +----------------+
                     |   |   |
          +----------+   |   +-----------+
          v              v               v
     +---------+    +---------+     +---------+
     | backend |    | backend |     | backend |   C++ socket servers
     |  :8080  |    |  :8080  |     |  :8080  |   /healthz  /metrics
     +---------+    +---------+     +---------+
          ^              ^               ^
          |   scrape /metrics (in-flight, latency, totals)
          |              |               |
          +--------------+---------------+
                        |
                        v
                +------------------+   docker API: start/stop backends
   host :8089    |    controller    |   decide scale up/down + cooldowns
                 | (autoscaler +    |   rewrite nginx upstream, reload
                 |  metrics + SSE)  |   stream fleet state to the dashboard
                +------------------+
                        |  SSE
                        v
                +------------------+
   host :8090    |    dashboard     |   animated fleet, request-flow,
                 | (React + SVG)    |   load-vs-fleet-size chart
                +------------------+
```

Everything comes up with **one command** (`docker compose up`). The controller manages backend
containers dynamically through the Docker API on a shared Compose network; nginx, the controller
and the dashboard are long-lived services.

### Components

| Component | Tech | Responsibility |
| :-- | :-- | :-- |
| Backend | C++ (Ubuntu build image) | Serve requests; expose `/healthz` and a scrapeable `/metrics` (in-flight, total, latency, uptime, host). A thread pool makes concurrency real; a tunable per-request work cost makes load controllable for demos. |
| Load balancer | nginx | Distribute requests; upstream list rewritten and hot-reloaded as the fleet changes; unhealthy backends removed with no dropped requests. |
| Controller | Python (FastAPI + Docker SDK) | Scrape backend metrics, decide scale up/down with watermarks and cooldowns, start/stop backend containers, rewrite + reload nginx, and stream live fleet state to the dashboard over SSE. |
| Load generator | Python CLI | Drive traffic with presets: steady, spike, ramp. |
| Dashboard | React + TypeScript + Vite + Tailwind | Animate backends appearing/disappearing and requests flowing; chart load against fleet size; a replay mode plays a recorded run for the hosted demo. |
| CI/CD | GitHub Actions + Jenkins | Actions builds and tests on every push; the Jenkins pipeline is kept. |

### Ports

Host-facing ports avoid ones already in use (8000, 8001, 5000): nginx **8088**, controller
**8089**, dashboard **8090**. Backends are internal to the Compose network and expose no host port.

## The autoscaling model

- The controller scrapes each backend's `/metrics` on a fixed interval.
- The scaling signal is **average in-flight requests per backend** (latency is shown alongside).
- **Scale up** when the average stays above a high watermark past a scale-up cooldown; **scale
  down** when it stays below a low watermark past a longer scale-down cooldown. Min and max fleet
  size bound it. Separate cooldowns stop it flapping.
- **No dropped requests:** a new backend is added to the upstream only after its health check
  passes; a removed backend is taken out of the upstream and drained before its container stops.
- The decision function is pure and unit-tested; the container actions are integration-tested.

## What ships this round

1. One-command bring-up with Docker Compose.
2. C++ backend with health and metrics endpoints and a real concurrency model.
3. An autoscaler with health-gated scale-up and drain-before-stop scale-down.
4. Live, zero-drop nginx upstream reloads.
5. A load generator with presets.
6. A measured scale-up/scale-down run with honest numbers and a plot.
7. A live dashboard, plus a replay mode for the hosted demo.
8. GitHub Actions CI; the Jenkins pipeline kept.
9. Landing-page README, docs, licence, changelog, contributor guide, good first issues, a release.

## Roadmap (later)

Switchable load-balancing algorithms compared live (round robin, least connections, consistent
hashing); chaos testing that kills backends mid-run; predictive/scheduled scaling; canary and
blue-green rollouts; a comparison with Kubernetes' Horizontal Pod Autoscaler; a C++ reverse proxy
replacing nginx; rewriting the server's thread pool to `epoll` with measured throughput gains.

## Delivery — three pull requests

### PR 1 — Foundation
- Docker Compose brings the starting fleet up with one command (nginx + a seed set of backends).
- C++ backend gains `/healthz` and a scrapeable `/metrics` (in-flight, total requests, latency,
  uptime, hostname), a **thread pool** so concurrency is real, and a tunable per-request work cost.
- A throughput benchmark (blocking loop vs thread pool) with numbers recorded by a rerunnable
  script — the first "measure the gain" result.
- C++ tests run in a container (endpoint behaviour and metrics format).
- GitHub Actions CI: build the backend image, run the C++ tests. Jenkins pipeline kept working.
- `docs/roadmap.md` (this file) and a README stub.

### PR 2 — Elasticity
- The controller: metrics scraping, the scaling decision with watermarks and cooldowns, container
  start/stop over the Docker API, nginx upstream rewrite + hot reload, health-gated add and
  drain-before-stop remove.
- The load generator with steady / spike / ramp presets.
- A measured scale-up and scale-down run: a script drives a ramp, records fleet size, latency and
  in-flight over time to CSV, and plots it; written up with real numbers, including anything that
  didn't go to plan.
- Unit tests for the decision function; an integration smoke test for a full scale cycle.
- CI extended to run the Python tests.

### PR 3 — Experience & launch
- The dashboard: animated fleet view (backends appear and vanish, requests flow to them), a
  load-vs-fleet-size chart, live state over SSE, and a replay mode that plays a recorded run.
- README rewritten as a landing page with a demo animation and badges.
- `docs/` (architecture, operating the platform, the measured runs), `CHANGELOG.md`,
  `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, an Apache-2.0 `LICENSE`.
- A handful of good first issues, the dashboard's replay demo published to GitHub Pages, and a
  tagged release.

Each pull request opens, waits for CI to pass, and merges before the next begins.
