import { afterEach, describe, expect, it, vi } from "vitest";
import { _reset, initAnalytics, track } from "../src/lib/analytics";

afterEach(() => {
  _reset();
  vi.unstubAllGlobals();
});

describe("analytics", () => {
  it("track is a no-op without GA id", () => {
    const gtag = vi.fn();
    vi.stubGlobal("window", { gtag });
    initAnalytics(undefined);
    track("vote", { park: "x" });
    expect(gtag).not.toHaveBeenCalled();
  });

  it("track forwards to gtag when initialised", () => {
    const calls: unknown[][] = [];
    vi.stubGlobal("window", { dataLayer: [] });
    initAnalytics("G-TEST");
    (window as any).gtag = (...a: unknown[]) => calls.push(a);
    track("vote", { park: "x" });
    expect(calls.at(-1)).toEqual(["event", "vote", { park: "x" }]);
  });
});
