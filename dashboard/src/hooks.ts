import { useCallback, useEffect, useRef, useState } from "react";
import { fetchReplay, fetchState } from "./api";
import { pushPoint } from "./lib/history";
import type { Config, HistoryPoint, ReplayData, Snapshot } from "./types";

const MAX_POINTS = 90;
const FRAME_MS = 280; // replay speed (recorded at 1 Hz)

export interface FleetStream {
  snapshot: Snapshot | null;
  config: Config | null;
  history: HistoryPoint[];
  error: string | null;
}

function toPoint(s: Snapshot & { t?: number }, t: number): HistoryPoint {
  return { t: s.t ?? t, fleet_size: s.fleet_size, signal_ms: s.signal_ms,
           offered: s.offered };
}

/** Poll the live controller once a second while enabled. */
export function useLiveFleet(enabled: boolean): FleetStream {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const t0 = useRef<number>(Date.now());

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const ctrl = new AbortController();

    const tick = async () => {
      try {
        const st = await fetchState(ctrl.signal);
        if (!alive) return;
        setConfig(st.config);
        setSnapshot(st);
        setError(null);
        const t = (Date.now() - t0.current) / 1000;
        setHistory((h) => pushPoint(h, toPoint(st, t), MAX_POINTS));
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => {
      alive = false;
      ctrl.abort();
      clearInterval(id);
    };
  }, [enabled]);

  return { snapshot, config, history, error };
}

export interface ReplayControls {
  playing: boolean;
  setPlaying: (p: boolean) => void;
  index: number;
  length: number;
  seek: (i: number) => void;
  restart: () => void;
}

/** Load a recorded run and play it back frame by frame. */
export function useReplayFleet(enabled: boolean): FleetStream & {
  controls: ReplayControls;
} {
  const [data, setData] = useState<ReplayData | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || data) return;
    fetchReplay().then(setData).catch((e) => setError((e as Error).message));
  }, [enabled, data]);

  useEffect(() => {
    if (!enabled || !data || !playing) return;
    const id = setInterval(() => {
      setIndex((i) => {
        if (i + 1 >= data.frames.length) {
          clearInterval(id);
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, FRAME_MS);
    return () => clearInterval(id);
  }, [enabled, data, playing]);

  const frames = data?.frames ?? [];
  const snapshot = frames[index] ?? null;
  const history = frames.slice(0, index + 1).map((f) => toPoint(f, f.t));

  const controls: ReplayControls = {
    playing,
    setPlaying,
    index,
    length: frames.length,
    seek: useCallback((i: number) => setIndex(i), []),
    restart: useCallback(() => {
      setIndex(0);
      setPlaying(true);
    }, []),
  };

  return { snapshot, config: data?.config ?? null, history, error, controls };
}
