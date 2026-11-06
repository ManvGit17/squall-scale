# Operations

## Running

```bash
docker compose up --build      # build and start everything
bash scripts/down.sh           # stop everything, incl. spawned backends
```

The controller spawns backends that are **not** part of the Compose project, so always tear down
with `scripts/down.sh` (plain `docker compose down` leaves them running).

| Service | URL | Notes |
| :-- | :-- | :-- |
| Dashboard | <http://localhost:8090> | Live, or replay if no controller is reachable. |
| Load balancer | <http://localhost:8088> | `/`, `/healthz`, `/metrics` all proxy to the fleet. |
| Controller | <http://localhost:8089/state> | Live fleet state as JSON; `/healthz` for liveness. |

## Driving load

```bash
python loadgen/loadgen.py steady --concurrency 32 --duration 30
python loadgen/loadgen.py ramp   --start 2 --end 100 --duration 60
python loadgen/loadgen.py spike  --base 4 --peak 80 --duration 45
python scripts/scale_run.py          # a full ramp→hold→idle cycle, recorded
```

## Tuning the autoscaler

All via environment variables (see [`docker-compose.yml`](../docker-compose.yml) and
[`controller/config.py`](../controller/config.py)):

| Variable | Default | Meaning |
| :-- | :-- | :-- |
| `MIN_BACKENDS` / `MAX_BACKENDS` | 2 / 6 | Fleet size bounds. |
| `HIGH_WATERMARK_MS` / `LOW_WATERMARK_MS` | 150 / 70 | Latency to scale up / down. |
| `UP_COOLDOWN_S` / `DOWN_COOLDOWN_S` | 10 / 25 | Minimum gap between scale actions. |
| `WORK_MS` | 40 | Simulated work per request on each backend. |
| `THREADS` | 8 | Worker threads per backend. |
| `INTERVAL_S` | 2 | Control-loop tick. |
| `DRAIN_S` | 5 | Grace to drain a backend before stopping it. |

Example — a snappier, smaller fleet:

```bash
MAX_BACKENDS=4 HIGH_WATERMARK_MS=120 UP_COOLDOWN_S=6 docker compose up --build
```

## Troubleshooting

- **Dashboard shows REPLAY, not LIVE.** The controller isn't reachable at `:8089`. Check
  `docker compose ps` and `docker logs squallscale-controller`.
- **`:8088` refuses connections at first.** The controller writes the nginx config on startup;
  give it a few seconds after `up`.
- **Backends linger after a crash.** `bash scripts/down.sh` removes anything labelled
  `squallscale.role=backend`.
- **Ports busy.** The host ports are 8088/8089/8090; change the left-hand side of the `ports:`
  entries in `docker-compose.yml` if they clash.
