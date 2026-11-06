import { useEffect, useState } from "react";
import Chart from "./components/Chart";
import Controls from "./components/Controls";
import FleetView from "./components/FleetView";
import Header from "./components/Header";
import { controllerReachable } from "./api";
import { useLiveFleet, useReplayFleet } from "./hooks";
import type { Mode } from "./types";

export default function App() {
  const [mode, setMode] = useState<Mode>("replay");
  const [canGoLive, setCanGoLive] = useState(false);
  const [decided, setDecided] = useState(false);

  // Auto-detect: use the live controller if it answers, else replay.
  useEffect(() => {
    controllerReachable().then((ok) => {
      setCanGoLive(ok);
      setMode(ok ? "live" : "replay");
      setDecided(true);
    });
  }, []);

  const live = useLiveFleet(decided && mode === "live");
  const replay = useReplayFleet(decided && mode === "replay");
  const stream = mode === "live" ? live : replay;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <Header mode={mode} snapshot={stream.snapshot} />

      <section className="mb-5 rounded-2xl border border-edge bg-panel/50 p-4">
        <Chart history={stream.history} config={stream.config} />
      </section>

      <section className="mb-5">
        <Controls
          mode={mode}
          canGoLive={canGoLive}
          onMode={setMode}
          replay={mode === "replay" ? replay.controls : null}
          snapshot={stream.snapshot}
        />
      </section>

      {stream.error && mode === "live" && (
        <p className="mb-4 rounded-lg border border-pink/40 bg-pink/10 px-3 py-2 text-sm text-pink">
          Controller unreachable ({stream.error}). Switch to Replay, or start the
          stack with <code>docker compose up</code>.
        </p>
      )}

      <section>
        {stream.snapshot ? (
          <FleetView backends={stream.snapshot.backends} />
        ) : (
          <p className="text-slate-400">Loading…</p>
        )}
      </section>

      <footer className="mt-8 text-center text-xs text-slate-500">
        A self-hosted autoscaling platform · the fleet grows and shrinks with load
      </footer>
    </div>
  );
}
