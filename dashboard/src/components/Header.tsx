import type { Mode, Snapshot } from "../types";

function Stat({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="rounded-xl border border-edge bg-panel px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`font-mono text-2xl ${accent}`}>{value}</div>
    </div>
  );
}

export default function Header({ mode, snapshot }: { mode: Mode; snapshot: Snapshot | null }) {
  const fleet = snapshot?.fleet_size ?? 0;
  const signal = snapshot?.signal_ms;
  const rps = (snapshot?.backends ?? []).reduce((s, b) => s + (b.recent_rps ?? 0), 0);

  return (
    <header className="mb-5">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">
            squall<span className="text-coral">scale</span>
          </h1>
          <p className="text-sm text-slate-400">watch the fleet breathe</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-mono ${
            mode === "live"
              ? "bg-mint/15 text-mint border border-mint/40"
              : "bg-sky/15 text-sky border border-sky/40"
          }`}
        >
          {mode === "live" ? "LIVE" : "REPLAY"}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        <Stat label="backends" value={String(fleet)} accent="text-coral" />
        <Stat
          label="latency signal"
          value={signal == null ? "—" : `${signal.toFixed(0)} ms`}
          accent="text-sky"
        />
        <Stat label="throughput" value={`${rps.toFixed(0)} rps`} accent="text-mint" />
      </div>
    </header>
  );
}
