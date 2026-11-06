import type { HistoryPoint } from "../types";

/** Append a point to a rolling window, keeping at most `max` points. */
export function pushPoint(
  history: HistoryPoint[],
  point: HistoryPoint,
  max: number,
): HistoryPoint[] {
  const next = [...history, point];
  return next.length > max ? next.slice(next.length - max) : next;
}

/** Round a value up to a readable axis maximum (…, 50, 100, 200, 250 …). */
export function niceMax(value: number): number {
  if (value <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(value)));
  for (const step of [1, 2, 2.5, 5, 10]) {
    const candidate = step * pow;
    if (candidate >= value) return candidate;
  }
  return 10 * pow;
}

/** Map a value in [0, max] to a y pixel within [top, top+height] (inverted). */
export function scaleY(value: number, max: number, top: number, height: number): number {
  const clamped = Math.max(0, Math.min(max, value));
  return top + height * (1 - clamped / max);
}
