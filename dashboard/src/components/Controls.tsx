import type { Mode, Snapshot } from "../types";
import type { ReplayControls } from "../hooks";

interface Props {
  mode: Mode;
  canGoLive: boolean;
  onMode: (m: Mode) => void;
  replay: ReplayControls | null;
  snapshot: Snapshot | null;
}

export default function Controls({ mode, canGoLive, onMode, replay, snapshot }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="inline-flex overflow-hidden rounded-lg border border-edge">
        <button
          className={`px-3 py-1.5 text-sm ${mode === "live" ? "bg-mint/20 text-mint" : "text-slate-400"}`}
          onClick={() => onMode("live")}
          disabled={!canGoLive}
          title={canGoLive ? "" : "No controller reachable"}
        >
          Live
        </button>
        <button
          className={`px-3 py-1.5 text-sm ${mode === "replay" ? "bg-sky/20 text-sky" : "text-slate-400"}`}
          onClick={() => onMode("replay")}
        >
          Replay
        </button>
      </div>

      {mode === "replay" && replay && (
        <div className="flex flex-1 items-center gap-3">
          <button
            className="rounded-lg border border-edge px-3 py-1.5 text-sm"
            onClick={() =>
              replay.index + 1 >= replay.length
                ? replay.restart()
                : replay.setPlaying(!replay.playing)
            }
          >
            {replay.index + 1 >= replay.length ? "↻ Restart" : replay.playing ? "❚❚ Pause" : "▶ Play"}
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, replay.length - 1)}
            value={replay.index}
            onChange={(e) => replay.seek(Number(e.target.value))}
            className="flex-1 accent-sky"
            aria-label="Scrub replay"
          />
          <span className="font-mono text-xs text-slate-400">
            offered {snapshot?.offered ?? 0}
          </span>
        </div>
      )}

      {mode === "live" && (
        <span className="text-xs text-slate-400">
          drive load:{" "}
          <code className="rounded bg-panel px-1.5 py-0.5 text-coral">
            python loadgen/loadgen.py ramp --start 2 --end 100 --duration 60
          </code>
        </span>
      )}
    </div>
  );
}
