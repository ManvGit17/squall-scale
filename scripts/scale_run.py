#!/usr/bin/env python3
"""Drive a ramp-then-idle load and record how the fleet scales to meet it.

Loads the balancer with a profile that ramps concurrency up, holds it, then
drops to idle. While it runs, it polls the controller's /state once a second
and records fleet size, the latency signal and offered concurrency. Afterwards
it writes a CSV, an SVG chart and a summary JSON with honest numbers.

  python scripts/scale_run.py

Standard library only. Requires the stack to be up (docker compose up).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "loadgen"))
from loadgen import LoadRunner  # noqa: E402

RESULTS = ROOT / "bench" / "results"


def profile(ramp_s: float, hold_s: float, peak: int):
    """Ramp 2 -> peak over ramp_s, hold peak for hold_s, then idle."""
    def sched(t: float) -> int:
        if t < ramp_s:
            return round(2 + (peak - 2) * (t / ramp_s))
        if t < ramp_s + hold_s:
            return peak
        return 0
    return sched


def poll_state(controller: str):
    with urllib.request.urlopen(f"{controller}/state", timeout=3) as r:
        return json.load(r)


def render_svg(rows: list[dict], cfg: dict) -> str:
    W, H = 900, 380
    pad_l, pad_r, pad_t, pad_b = 60, 55, 30, 45
    pw, ph = W - pad_l - pad_r, H - pad_t - pad_b

    t_max = max((r["t"] for r in rows), default=1.0) or 1.0
    lat_max = max([r["signal_ms"] or 0 for r in rows] + [cfg["high_watermark_ms"]]) * 1.15
    fleet_max = max([r["fleet_size"] for r in rows] + [cfg["max_backends"]])

    def x(t):   return pad_l + pw * (t / t_max)
    def yl(v):  return pad_t + ph * (1 - v / lat_max)
    def yf(v):  return pad_t + ph * (1 - v / fleet_max)

    def poly(points):
        return " ".join(f"{px:.1f},{py:.1f}" for px, py in points)

    lat_pts = [(x(r["t"]), yl(r["signal_ms"] or 0)) for r in rows]
    # Fleet size as a step line.
    fleet_pts = []
    for i, r in enumerate(rows):
        if i:
            fleet_pts.append((x(r["t"]), yf(rows[i - 1]["fleet_size"])))
        fleet_pts.append((x(r["t"]), yf(r["fleet_size"])))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="system-ui,sans-serif" font-size="12">',
        f'<rect width="{W}" height="{H}" fill="white"/>',
        # axes
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#333"/>',
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#333"/>',
        # watermarks
        f'<line x1="{pad_l}" y1="{yl(cfg["high_watermark_ms"]):.1f}" '
        f'x2="{pad_l+pw}" y2="{yl(cfg["high_watermark_ms"]):.1f}" '
        f'stroke="#e0567c" stroke-dasharray="4 3"/>',
        f'<text x="{pad_l+pw}" y="{yl(cfg["high_watermark_ms"])-4:.1f}" '
        f'text-anchor="end" fill="#e0567c">high {cfg["high_watermark_ms"]:.0f}ms</text>',
        f'<line x1="{pad_l}" y1="{yl(cfg["low_watermark_ms"]):.1f}" '
        f'x2="{pad_l+pw}" y2="{yl(cfg["low_watermark_ms"]):.1f}" '
        f'stroke="#3b9" stroke-dasharray="4 3"/>',
        f'<text x="{pad_l+pw}" y="{yl(cfg["low_watermark_ms"])-4:.1f}" '
        f'text-anchor="end" fill="#3b9">low {cfg["low_watermark_ms"]:.0f}ms</text>',
        # series
        f'<polyline fill="none" stroke="#f0a088" stroke-width="2.5" '
        f'points="{poly(fleet_pts)}"/>',
        f'<polyline fill="none" stroke="#4679e0" stroke-width="2" '
        f'points="{poly(lat_pts)}"/>',
        # labels
        f'<text x="{pad_l}" y="18" fill="#4679e0">latency (ms)</text>',
        f'<text x="{W-pad_r}" y="18" fill="#f0a088" text-anchor="end">fleet size</text>',
        f'<text x="{pad_l+pw/2}" y="{H-10}" text-anchor="middle" fill="#333">'
        f'time (s)</text>',
    ]
    # y ticks (latency left, fleet right)
    for frac in (0, 0.5, 1.0):
        parts.append(f'<text x="{pad_l-8}" y="{yl(lat_max*frac)+4:.1f}" '
                     f'text-anchor="end" fill="#4679e0">{lat_max*frac:.0f}</text>')
    for v in range(0, fleet_max + 1):
        parts.append(f'<text x="{pad_l+pw+8}" y="{yf(v)+4:.1f}" '
                     f'fill="#f0a088">{v}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://localhost:8088")
    ap.add_argument("--controller", default="http://localhost:8089")
    ap.add_argument("--ramp", type=float, default=30)
    ap.add_argument("--hold", type=float, default=20)
    ap.add_argument("--idle", type=float, default=35)
    ap.add_argument("--peak", type=int, default=64)
    args = ap.parse_args()

    total = args.ramp + args.hold + args.idle
    sched = profile(args.ramp, args.hold, args.peak)
    runner = LoadRunner(args.url, sched, total, args.peak)

    rows: list[dict] = []
    cfg_holder: dict = {}

    def record():
        start = time.monotonic()
        while time.monotonic() - start < total + 1:
            try:
                st = poll_state(args.controller)
            except OSError:
                time.sleep(1)
                continue
            if not cfg_holder:
                cfg_holder.update(st["config"])
            t = round(time.monotonic() - start, 1)
            in_flight = sum(b.get("in_flight", 0) or 0
                            for b in st["backends"] if b.get("healthy"))
            rps = sum(b.get("recent_rps", 0) or 0
                      for b in st["backends"] if b.get("healthy"))
            rows.append({"t": t, "fleet_size": st["fleet_size"],
                         "signal_ms": st["signal_ms"],
                         "offered": sched(t), "in_flight": round(in_flight, 1),
                         "rps": round(rps, 1)})
            time.sleep(1)

    poller = threading.Thread(target=record, daemon=True)
    poller.start()
    print(f"driving load for {total:.0f}s (ramp {args.ramp}s, hold {args.hold}s, "
          f"idle {args.idle}s, peak {args.peak})")
    runner.run()
    poller.join(timeout=5)

    RESULTS.mkdir(parents=True, exist_ok=True)
    # CSV
    cols = ["t", "offered", "fleet_size", "signal_ms", "in_flight", "rps"]
    csv = [",".join(cols)]
    for r in rows:
        csv.append(",".join(str(r.get(c, "")) for c in cols))
    (RESULTS / "scaling-run.csv").write_text("\n".join(csv) + "\n", encoding="utf-8")

    # SVG
    (RESULTS / "scaling-run.svg").write_text(
        render_svg(rows, cfg_holder), encoding="utf-8")

    # Summary
    peak_fleet = max((r["fleet_size"] for r in rows), default=0)
    peak_lat = max((r["signal_ms"] or 0 for r in rows), default=0)
    final_fleet = rows[-1]["fleet_size"] if rows else 0
    first_up = next((r["t"] for r in rows if r["fleet_size"] > cfg_holder.get(
        "min_backends", 2)), None)
    summary = {
        "params": {"ramp_s": args.ramp, "hold_s": args.hold,
                   "idle_s": args.idle, "peak_concurrency": args.peak},
        "config": cfg_holder,
        "min_fleet": min((r["fleet_size"] for r in rows), default=0),
        "peak_fleet": peak_fleet,
        "final_fleet": final_fleet,
        "peak_signal_ms": round(peak_lat, 1),
        "first_scale_up_at_s": first_up,
        "samples": len(rows),
    }
    (RESULTS / "scaling-run.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"wrote {RESULTS/'scaling-run.csv'}, scaling-run.svg, scaling-run.json")


if __name__ == "__main__":
    main()
