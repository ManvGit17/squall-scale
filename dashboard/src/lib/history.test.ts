import { describe, expect, it } from "vitest";
import { niceMax, pushPoint, scaleY } from "./history";
import type { HistoryPoint } from "../types";

const pt = (t: number): HistoryPoint => ({ t, fleet_size: 2, signal_ms: 0 });

describe("pushPoint", () => {
  it("appends within the window", () => {
    const h = pushPoint([pt(0)], pt(1), 5);
    expect(h).toHaveLength(2);
    expect(h[1].t).toBe(1);
  });

  it("drops the oldest past the window", () => {
    let h: HistoryPoint[] = [];
    for (let i = 0; i < 10; i++) h = pushPoint(h, pt(i), 5);
    expect(h).toHaveLength(5);
    expect(h[0].t).toBe(5);
    expect(h[4].t).toBe(9);
  });
});

describe("niceMax", () => {
  it("rounds up to readable bounds", () => {
    expect(niceMax(0)).toBe(1);
    expect(niceMax(42)).toBe(50);
    expect(niceMax(150)).toBe(200);
    expect(niceMax(195)).toBe(200);
  });
});

describe("scaleY", () => {
  it("inverts and clamps", () => {
    expect(scaleY(0, 100, 0, 200)).toBe(200);
    expect(scaleY(100, 100, 0, 200)).toBe(0);
    expect(scaleY(50, 100, 0, 200)).toBe(100);
    expect(scaleY(999, 100, 0, 200)).toBe(0);
  });
});
