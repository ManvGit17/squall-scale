"""Docker-facing fleet operations: create and drain backends, reload nginx.

This is the side-effecting layer. The scaling policy (scaling.py) and metrics
parsing (scrape.py) stay pure and are tested on their own; here we talk to the
Docker API and over HTTP to the backends.
"""
from __future__ import annotations

import time
import urllib.request

import docker

from config import Config
from nginx_conf import render_nginx_conf
from scrape import Sample


def http_get(url: str, timeout: float = 2.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8", "replace")


class Fleet:
    def __init__(self, client: docker.DockerClient, cfg: Config):
        self.client = client
        self.cfg = cfg
        self._counter = 0

    # -- discovery ---------------------------------------------------------
    def backends(self) -> list:
        """Running backend containers managed by this controller."""
        return self.client.containers.list(
            filters={"label": f"{self.cfg.backend_label}=backend",
                     "status": "running"})

    def backend_names(self) -> list[str]:
        return [c.name for c in self.backends()]

    def adopt_counter(self) -> None:
        """Continue naming past any backends already running (after restart)."""
        highest = 0
        for c in self.backends():
            tail = c.name.rsplit("-", 1)[-1]
            if tail.isdigit():
                highest = max(highest, int(tail))
        self._counter = highest

    # -- lifecycle ---------------------------------------------------------
    def create_backend(self) -> str:
        self._counter += 1
        name = f"squallscale-backend-{self._counter}"
        self.client.containers.run(
            self.cfg.backend_image,
            name=name,
            detach=True,
            network=self.cfg.network,
            environment={
                "PORT": str(self.cfg.backend_port),
                "WORK_MS": str(self.cfg.backend_work_ms),
                "THREADS": str(self.cfg.backend_threads),
            },
            labels={f"{self.cfg.backend_label}": "backend"},
        )
        self._wait_healthy(name)
        return name

    def _wait_healthy(self, name: str) -> None:
        url = f"http://{name}:{self.cfg.backend_port}/healthz"
        deadline = time.time() + self.cfg.health_timeout_s
        while time.time() < deadline:
            try:
                if "ok" in http_get(url, timeout=2.0):
                    return
            except OSError:
                time.sleep(0.3)
        raise RuntimeError(f"backend {name} never became healthy")

    def remove_all(self) -> None:
        """Force-remove every managed backend (used on controller shutdown)."""
        for c in self.backends():
            try:
                c.remove(force=True)
            except docker.errors.APIError:
                pass

    def remove_backend(self, name: str) -> None:
        """Stop a backend. The caller has already taken it out of nginx and
        waited the drain window; the container's own SIGTERM drain is a second
        safety net."""
        try:
            c = self.client.containers.get(name)
        except docker.errors.NotFound:
            return
        c.stop(timeout=int(self.cfg.drain_s) + 5)
        c.remove(force=True)

    # -- load balancer -----------------------------------------------------
    def write_and_reload(self, backend_names: list[str]) -> None:
        conf = render_nginx_conf(backend_names, port=self.cfg.backend_port)
        with open(self.cfg.nginx_conf_path, "w", encoding="utf-8") as f:
            f.write(conf)
        lb = self.client.containers.get(self.cfg.lb_container)
        code, out = lb.exec_run(["nginx", "-s", "reload"])
        if code != 0:
            raise RuntimeError(f"nginx reload failed: {out!r}")

    def scrape(self, name: str) -> Sample | None:
        url = f"http://{name}:{self.cfg.backend_port}/metrics"
        try:
            return Sample.from_text(http_get(url, timeout=2.0))
        except OSError:
            return None
