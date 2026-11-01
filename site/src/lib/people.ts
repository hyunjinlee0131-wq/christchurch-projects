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
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
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
