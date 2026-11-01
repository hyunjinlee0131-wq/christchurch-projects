import { describe, expect, it } from "vitest";
import data from "../src/data/best_park/parks.json";
import { rankParks, scorePark } from "../src/lib/scoring";

const W = data.weights as Record<string, number>;

describe("scoring", () => {
  it("scorePark matches python for default weights", () => {
    for (const p of data.parks) expect(scorePark(p.pct, W, W)).toBe(p.score); // every park, exactly
  });

  it("all-zero weights fall back to default", () => {
    const zero = Object.fromEntries(Object.keys(W).map((k) => [k, 0]));
    const p = data.parks[0];
    expect(scorePark(p.pct, zero, W)).toBeCloseTo(p.score, 1);
    expect(Number.isNaN(scorePark(p.pct, zero, W))).toBe(false);
  });

  it("rankParks orders by personal score, ties by area", () => {
    const parks = [
      { id: "a", area_ha: 1, pct: { play: 0.5 }, score: 0 },
      { id: "b", area_ha: 5, pct: { play: 0.5 }, score: 0 },
      { id: "c", area_ha: 1, pct: { play: 0.9 }, score: 0 },
    ];
    const ranked = rankParks(parks, { play: 1 }, { play: 1 });
    expect(ranked.map((p) => p.id)).toEqual(["c", "b", "a"]);
    expect(ranked.map((p) => p.personalRank)).toEqual([1, 2, 3]);
  });
});
