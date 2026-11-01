import { describe, expect, it } from "vitest";
import { bboxOf } from "../src/lib/geo";

describe("bboxOf", () => {
  it("handles polygons", () => {
    expect(bboxOf({ type: "Polygon", coordinates: [[[172.6, -43.5], [172.7, -43.5], [172.7, -43.4], [172.6, -43.5]]] }))
      .toEqual([172.6, -43.5, 172.7, -43.4]);
  });
  it("handles multipolygons", () => {
    expect(bboxOf({ type: "MultiPolygon", coordinates: [[[[1, 1], [2, 2], [1, 1]]], [[[5, -1], [6, 0], [5, -1]]]] }))
      .toEqual([1, -1, 6, 2]);
  });
});
