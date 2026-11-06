import { useEffect, useRef } from "react";
import type { Backend } from "../types";

function shortName(name: string): string {
  const tail = name.split("-").pop();
  return tail ? `#${tail}` : name;
}

function BackendCard({ b }: { b: Backend }) {
  const rps = b.recent_rps ?? 0;
  const latency = b.recent_latency_ms;
  // Faster pulse the more requests are flowing (clamped to a sane range).
  const period = rps > 0 ? Math.max(0.5, Math.min(2.5, 120 / rps)) : 0;
  const mountRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    mountRef.current?.classList.add("card-enter");
  }, []);

  return (
    <div
      ref={mountRef}
      className={`rounded-xl border border-edge bg-panel p-4 ${
        b.healthy ? "" : "opacity-40"
      }`}
      style={period ? { animation: `pulse-ring ${period}s ease-out infinite` } : undefined}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-coral">{shortName(b.name)}</span>
        <span
          className={`h-2 w-2 rounded-full ${b.healthy ? "bg-mint" : "bg-pink"}`}
          title={b.healthy ? "healthy" : "unhealthy"}
        />
      </div>
      <dl className="mt-3 space-y-1 text-sm">
        <div className="flex justify-between">
          <dt className="text-slate-400">in flight</dt>
          <dd className="font-mono">{b.in_flight ?? 0}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-400">latency</dt>
          <dd className="font-mono">
            {latency == null ? "—" : `${latency.toFixed(0)} ms`}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-400">throughput</dt>
          <dd className="font-mono">{rps.toFixed(0)} rps</dd>
        </div>
      </dl>
    </div>
  );
}

export default function FleetView({ backends }: { backends: Backend[] }) {
  const sorted = [...backends].sort((a, b) => a.name.localeCompare(b.name));
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {sorted.map((b) => (
        <BackendCard key={b.name} b={b} />
      ))}
    </div>
  );
}
