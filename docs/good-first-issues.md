# Good first issues

Starting points for new contributors. Each is self-contained and touches one part of the system.
Pick one, open an issue to claim it, and see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Backend (C++)

1. **Make `WORK_MS` jitter configurable.** Add a `WORK_JITTER_MS` so each request's simulated work
   varies a little, for a more realistic latency distribution. Unit-test the clamping.
2. **Expose a p95 latency metric.** Keep a small reservoir of recent request durations and add a
   `squallscale_request_duration_p95_seconds` gauge. Cover the reservoir logic with a test.
3. **Add a `/version` endpoint** that returns a build identifier, and surface it in `/state`.

## Controller (Python)

4. **Choose the scale-down victim by load**, not by newest index — drain the backend with the lowest
   recent throughput. Add a unit test for the selection.
5. **Add a `max_step` to scaling** so the fleet can grow by more than one backend per tick under a
   steep spike. Keep it bounded and tested.
6. **Record an action history endpoint** (`/history`) from the data the controller already keeps, so
   the dashboard can show a timeline of scale events.

## Dashboard (React)

7. **Add a sparkline of throughput** per backend card.
8. **Persist the chosen mode** (live/replay) in the URL so a view can be shared.
9. **Show scale events on the chart** as vertical markers (needs issue 6).

## Platform

10. **A `make` or task runner** wrapping the common commands (`up`, `down`, `load`, `bench`, `test`).
11. **A second load-balancing strategy** (least-connections) selectable by env var, with the
    dashboard labelling which is active — a first step toward the roadmap's "algorithms compared
    live."
