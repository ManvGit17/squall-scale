export interface Backend {
  name: string;
  healthy: boolean;
  in_flight?: number;
  recent_latency_ms?: number | null;
  recent_rps?: number | null;
}

export interface Config {
  min_backends: number;
  max_backends: number;
  high_watermark_ms: number;
  low_watermark_ms: number;
  up_cooldown_s: number;
  down_cooldown_s: number;
}

export interface Snapshot {
  fleet_size: number;
  signal_ms: number | null;
  offered?: number;
  backends: Backend[];
}

export interface HistoryPoint {
  t: number;
  fleet_size: number;
  signal_ms: number | null;
  offered?: number;
}

export interface ReplayData {
  config: Config;
  params: Record<string, number>;
  frames: (Snapshot & { t: number })[];
}

export type Mode = "live" | "replay";
