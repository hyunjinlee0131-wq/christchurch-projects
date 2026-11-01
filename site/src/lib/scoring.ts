// Personal park ranking: same formula as projects/best_park/score.py `score()`.
export type Weights = Record<string, number>;

export function scorePark(pct: Record<string, number>, w: Weights, fallback: Weights): number {
  let weights = w;
  if (Object.values(w).reduce((a, b) => a + b, 0) === 0) weights = fallback;
  let total = 0;
  let sum = 0;
  for (const [k, v] of Object.entries(weights)) {
    total += v;
    sum += v * (pct[k] ?? 0);
  }
  return total === 0 ? 0 : Math.round((1000 * sum) / total) / 10;
}

export function allZero(w: Weights): boolean {
  return Object.values(w).every((v) => v === 0);
}

export function rankParks<T extends { pct: Record<string, number>; area_ha: number }>(
  parks: T[],
  w: Weights,
  fallback: Weights,
): (T & { personalScore: number; personalRank: number })[] {
  return parks
    .map((p) => ({ ...p, personalScore: scorePark(p.pct, w, fallback) }))
    .sort((a, b) => b.personalScore - a.personalScore || b.area_ha - a.area_ha)
    .map((p, i) => ({ ...p, personalRank: i + 1 }));
}
