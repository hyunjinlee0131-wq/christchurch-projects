import { describe, expect, it } from "vitest";
import { SORTS, formatFactor, matchesName, sortParks } from "../src/lib/parklist";

const parks = [
  { id: "a", name: "Ōtākaro Park", rank: 2, area_ha: 1, raw: { bbq: 0, size: 1, dogs: 0, trees: 10.4 } },
  { id: "b", name: "Hagley Park", rank: 1, area_ha: 50, raw: { bbq: 3, size: 50, dogs: 1, trees: 30 } },
  { id: "c", name: "St Paul's Reserve", rank: 3, area_ha: 2, raw: { bbq: 3, size: 2, dogs: 0, trees: 5 } },
];

describe("sortParks", () => {
  it("overall score follows the data rank", () => {
    expect(sortParks(parks, "score").map((p) => p.id)).toEqual(["b", "a", "c"]);
  });
  it("sorts by a factor, most first, ties by data rank", () => {
    expect(sortParks(parks, "bbq").map((p) => p.id)).toEqual(["b", "c", "a"]);
  });
  it("does not mutate the input", () => {
    const copy = parks.map((p) => p.id);
    sortParks(parks, "size");
    expect(parks.map((p) => p.id)).toEqual(copy);
  });
  it("offers every factor plus overall", () => {
    expect(SORTS.map((s) => s.key)).toEqual(["score", "play", "seating", "bbq", "water", "sport", "dogs", "trees", "size"]);
  });
});

describe("matchesName", () => {
  it("ignores case, macrons and apostrophes", () => {
    expect(matchesName("Ōtākaro Park", "otakaro")).toBe(true);
    expect(matchesName("St Paul's Reserve", "pauls")).toBe(true);
    expect(matchesName("Hagley Park", "HAGLEY")).toBe(true);
    expect(matchesName("Hagley Park", "jellie")).toBe(false);
  });
  it("empty query matches everything", () => {
    expect(matchesName("Anything", "  ")).toBe(true);
  });
});

describe("formatFactor", () => {
  it("formats values readably", () => {
    expect(formatFactor("bbq", 1)).toBe("1 barbecue");
    expect(formatFactor("bbq", 3)).toBe("3 barbecues");
    expect(formatFactor("dogs", 1)).toBe("Yes");
    expect(formatFactor("dogs", 0)).toBe("No");
    expect(formatFactor("trees", 10.4)).toBe("10 per ha");
    expect(formatFactor("size", 12.345)).toBe("12.3 ha");
  });
});
