// Tiny GeoJSON helpers (lon/lat).
type Geometry = { type: "Polygon"; coordinates: number[][][] } | { type: "MultiPolygon"; coordinates: number[][][][] };

/** [west, south, east, north] of a park outline. */
export function bboxOf(g: Geometry): [number, number, number, number] {
  const rings = g.type === "Polygon" ? g.coordinates : g.coordinates.flat();
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  for (const ring of rings) for (const [x, y] of ring) {
    if (x < w) w = x; if (x > e) e = x; if (y < s) s = y; if (y > n) n = y;
  }
  return [w, s, e, n];
}
