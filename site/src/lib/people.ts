// People's Choice (votes) next to the data ranking — never blended into one number.
type Park = { id: string; name: string; rank: number };
export type Voted<T> = T & { votes: number; peopleRank: number };

export function peopleRanking<T extends Park>(parks: T[], counts: Record<string, number>): Voted<T>[] {
  return parks
    .filter((p) => (counts[p.id] ?? 0) > 0)
    .map((p) => ({ ...p, votes: counts[p.id] }))
    .sort((a, b) => b.votes - a.votes || a.rank - b.rank)
    .map((p, i) => ({ ...p, peopleRank: i + 1 }));
}

export function dataVsPeople<T extends Park>(parks: T[], counts: Record<string, number>, minVotes = 20, n = 5) {
  // Only votes for real parks count (test rows or junk ids must not unlock this section).
  const total = parks.reduce((sum, p) => sum + (counts[p.id] ?? 0), 0);
  if (total < minVotes) return null;
  // Compare positions among voted parks only, so the gap means something.
  const voted = peopleRanking(parks, counts);
  const byData = [...voted].sort((a, b) => a.rank - b.rank).map((p, i) => ({ ...p, dataPos: i + 1 }));
  const gaps = byData.map((p) => ({ ...p, gap: p.dataPos - p.peopleRank }));
  return {
    total,
    underrated: gaps.filter((p) => p.gap > 0).sort((a, b) => b.gap - a.gap).slice(0, n),
    overrated: gaps.filter((p) => p.gap < 0).sort((a, b) => a.gap - b.gap).slice(0, n),
  };
}

/** People's Choice podium: the top 3 get the fancy cards, #4–5 the smaller ones. */
export function podium<T>(ranked: T[]): { top3: T[]; runnersUp: T[] } {
  return { top3: ranked.slice(0, 3), runnersUp: ranked.slice(3, 5) };
}

/** What the map needs to place a People's Choice medal marker. */
export type PeoplesTop = { id: string; name: string; slug: string; lon: number; lat: number; votes: number };
