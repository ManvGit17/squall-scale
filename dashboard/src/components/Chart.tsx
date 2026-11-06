import { niceMax, scaleY } from "../lib/history";
import type { Config, HistoryPoint } from "../types";

interface Props {
  history: HistoryPoint[];
  config: Config | null;
}

const W = 900;
const H = 260;
const PAD = { l: 44, r: 44, t: 16, b: 24 };

export default function Chart({ history, config }: Props) {
  const pw = W - PAD.l - PAD.r;
  const ph = H - PAD.t - PAD.b;

  const high = config?.high_watermark_ms ?? 150;
  const low = config?.low_watermark_ms ?? 70;
  const latMax = niceMax(
    Math.max(high, ...history.map((p) => p.signal_ms ?? 0)),
  );
  const fleetMax = Math.max(
    config?.max_backends ?? 6,
    ...history.map((p) => p.fleet_size),
  );

  const n = Math.max(1, history.length - 1);
  const x = (i: number) => PAD.l + (pw * i) / Math.max(1, Math.min(n, 89));
  const yLat = (v: number) => scaleY(v, latMax, PAD.t, ph);
  const yFleet = (v: number) => scaleY(v, fleetMax, PAD.t, ph);

  const latPts = history
    .map((p, i) => `${x(i).toFixed(1)},${yLat(p.signal_ms ?? 0).toFixed(1)}`)
    .join(" ");

  const fleetPts: string[] = [];
  history.forEach((p, i) => {
    if (i) fleetPts.push(`${x(i).toFixed(1)},${yFleet(history[i - 1].fleet_size).toFixed(1)}`);
    fleetPts.push(`${x(i).toFixed(1)},${yFleet(p.fleet_size).toFixed(1)}`);
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
         aria-label="Latency and fleet size over time">
      {/* axes */}
      <line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={PAD.t + ph} stroke="#2b3a4d" />
      <line x1={PAD.l} y1={PAD.t + ph} x2={PAD.l + pw} y2={PAD.t + ph} stroke="#2b3a4d" />

      {/* watermarks */}
      <line x1={PAD.l} y1={yLat(high)} x2={PAD.l + pw} y2={yLat(high)}
            stroke="#e0567c" strokeDasharray="4 3" opacity={0.8} />
      <text x={PAD.l + pw} y={yLat(high) - 4} textAnchor="end" fill="#e0567c" fontSize="11">
        scale-up {high}ms
      </text>
      <line x1={PAD.l} y1={yLat(low)} x2={PAD.l + pw} y2={yLat(low)}
            stroke="#3bd9a0" strokeDasharray="4 3" opacity={0.8} />
      <text x={PAD.l + pw} y={yLat(low) - 4} textAnchor="end" fill="#3bd9a0" fontSize="11">
        scale-down {low}ms
      </text>

      {/* fleet size (step) and latency (line) */}
      {fleetPts.length > 0 && (
        <polyline fill="none" stroke="#f0a088" strokeWidth={2.5} points={fleetPts.join(" ")} />
      )}
      {history.length > 1 && (
        <polyline fill="none" stroke="#4679e0" strokeWidth={2} points={latPts} />
      )}

      {/* axis labels */}
      <text x={PAD.l} y={12} fill="#4679e0" fontSize="11">latency (ms)</text>
      <text x={W - PAD.r} y={12} fill="#f0a088" fontSize="11" textAnchor="end">fleet size</text>
      <text x={PAD.l - 6} y={yLat(latMax) + 4} textAnchor="end" fill="#4679e0" fontSize="10">
        {latMax}
      </text>
      <text x={PAD.l - 6} y={yLat(0) + 4} textAnchor="end" fill="#4679e0" fontSize="10">0</text>
      <text x={W - PAD.r + 6} y={yFleet(fleetMax) + 4} fill="#f0a088" fontSize="10">{fleetMax}</text>
      <text x={W - PAD.r + 6} y={yFleet(0) + 4} fill="#f0a088" fontSize="10">0</text>
    </svg>
  );
}
