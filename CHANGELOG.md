# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-11-06

First release: a self-hosted autoscaling platform built up over three milestones.

### Foundation
- One-command fleet under Docker Compose.
- C++ backend on a thread pool with `/healthz` and a Prometheus `/metrics` endpoint, graceful
  drain, and a tunable per-request work cost.
- A thread-pool throughput benchmark with recorded results.
- C++ unit tests and GitHub Actions CI; the Jenkins pipeline kept.
- Apache-2.0 license.

### Elasticity
- Controller that autoscales the fleet on recent request latency, with watermarks, cooldowns and
  min/max bounds; health-gated scale-up and drained scale-down; live nginx upstream reloads; and a
  `/state` API.
- Load generator with `steady`, `spike` and `ramp` presets.
- A measured scale-up/scale-down run recorded to `bench/results/` and written up in
  `docs/elasticity.md`.
- The backend measures latency from acceptance, so queue wait is visible to the autoscaler.

### Experience & launch
- A React dashboard that animates the fleet: backend cards appear, vanish and pulse with request
  flow, and a chart plots latency against fleet size. Runs live, or replays a recorded run.
- Landing-page README, architecture and operations docs, contributor guide, security policy and
  code of conduct.
- Dashboard build/test in CI and an end-to-end fleet smoke.

[Unreleased]: https://github.com/ManvGit17/squall-scale/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ManvGit17/squall-scale/releases/tag/v0.1.0
