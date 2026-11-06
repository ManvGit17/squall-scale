# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Dashboard** — a React single-page app that animates the fleet: backend cards appear, vanish and
  pulse with request flow, and a chart plots latency against fleet size with the scaling watermarks.
  Runs live against the controller, or replays a recorded run (so it works with no backend).
- **Landing-page README**, architecture and operations docs, contributor guide, security policy and
  code of conduct.

## [0.2.0] — Elasticity

### Added
- **Controller** that autoscales the fleet on recent request latency, with watermarks, cooldowns and
  min/max bounds; health-gated scale-up and drained scale-down; live nginx upstream reloads; and a
  `/state` API.
- **Load generator** with `steady`, `spike` and `ramp` presets.
- A measured scale-up/scale-down run recorded to `bench/results/` and written up in
  `docs/elasticity.md`.
- Controller unit tests and an end-to-end CI job.

### Changed
- The backend now measures latency from acceptance, so queue wait is included and saturation is
  visible to the autoscaler.
- Compose is now controller-owned: it builds the backend image and runs the load balancer and
  controller, which manage the backends.

## [0.1.0] — Foundation

### Added
- One-command fleet under Docker Compose.
- C++ backend on a thread pool with `/healthz` and a Prometheus `/metrics` endpoint, graceful drain,
  and a tunable per-request work cost.
- A thread-pool throughput benchmark with recorded results.
- C++ unit tests and GitHub Actions CI; the Jenkins pipeline kept.
- Apache-2.0 license.
