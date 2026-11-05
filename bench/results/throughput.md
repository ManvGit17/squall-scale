# Thread-pool throughput

Generated 2026-11-05T16:28:59Z.

Each run: 32 concurrent clients, closed loop, 8s, 40ms simulated work per request.

| Workers | Throughput (rps) | p50 (ms) | p95 (ms) | p99 (ms) | Speedup vs 1 |
| ------: | ---------------: | -------: | -------: | -------: | -----------: |
| 1 | 24.8 | 1287.7 | 1288.8 | 1289.1 | 1.0x |
| 8 | 198.3 | 160.8 | 161.8 | 162.4 | 8.0x |
| 16 | 397.7 | 80.3 | 82.6 | 83.9 | 16.04x |

One worker is the serialized baseline: it handles a single request at a time, like the original blocking accept loop. With simulated per-request work, extra workers let requests overlap, so throughput rises roughly with the worker count until the host runs out of room.
