# Contributing

Thanks for your interest. This is a small project with room to grow — see the
[good first issues](docs/good-first-issues.md) for starting points.

## Development setup

You need Docker (with Compose), and — for running tests outside containers — Python 3.12 and
Node 20+.

```bash
docker compose up --build        # the whole platform
bash scripts/down.sh             # tear down
```

## Running the tests

```bash
docker build --target test backend           # C++ unit tests
cd controller && python -m pytest tests       # controller unit tests
cd dashboard && npm ci && npm test            # dashboard unit test
bash scripts/smoke.sh                          # end-to-end, against a running fleet
```

CI runs all of these on every push and pull request; please make sure they pass locally first.

## Pull requests

- Work on a feature branch; keep the default branch clean.
- Keep commits small and in [Conventional Commits](https://www.conventionalcommits.org/) style
  (`feat:`, `fix:`, `docs:`, `build:`, `ci:`, `test:`, `chore:`).
- Back new behaviour with a test, and keep claims in the README or docs tied to a script anyone can
  rerun.
- Open a pull request and let CI pass before asking for review.

## Code style

- **C++** — C++17, dependency-light; keep pure logic in headers so it can be unit-tested without
  sockets.
- **Python** — standard library where practical; keep the scaling policy and parsing pure and
  tested, separate from the Docker-facing code.
- **TypeScript** — the dashboard builds with `strict` on; keep pure helpers testable.
