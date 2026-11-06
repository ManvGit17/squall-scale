import type { Config, ReplayData, Snapshot } from "./types";

// The controller API base. Defaults to the local controller; override with
// ?api=http://host:8089 when serving the dashboard elsewhere.
export function apiBase(): string {
  const param = new URLSearchParams(location.search).get("api");
  return param ?? "http://localhost:8089";
}

export interface StateResponse extends Snapshot {
  config: Config;
}

export async function fetchState(signal?: AbortSignal): Promise<StateResponse> {
  const res = await fetch(`${apiBase()}/state`, { signal });
  if (!res.ok) throw new Error(`state ${res.status}`);
  return res.json();
}

export async function fetchReplay(): Promise<ReplayData> {
  // Relative to the deployed base, so it works at any path.
  const res = await fetch("./replay.json");
  if (!res.ok) throw new Error(`replay ${res.status}`);
  return res.json();
}

/** True if the live controller is reachable. */
export async function controllerReachable(): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch(`${apiBase()}/healthz`, { signal: ctrl.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}
