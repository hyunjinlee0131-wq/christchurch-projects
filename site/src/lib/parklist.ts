// Leaderboard helpers: sort by overall score or by any single factor, and search by name.
export type SortKey = "score" | "play" | "seating" | "bbq" | "water" | "sport" | "dogs" | "trees" | "size";

export const SORTS: { key: SortKey; label: string; column: string }[] = [
  { key: "score", label: "Overall score", column: "" },
  { key: "play", label: "Most play equipment", column: "Play equipment" },
  { key: "seating", label: "Most seats & picnic tables", column: "Seats & tables" },
  { key: "bbq", label: "Most barbecues", column: "Barbecues" },
  { key: "water", label: "Most drinking water & showers", column: "Water" },
  { key: "sport", label: "Most sports fields", column: "Sports fields" },
  { key: "dogs", label: "Has a dog exercise area", column: "Dog area" },
  { key: "trees", label: "Most trees per hectare", column: "Trees" },
  { key: "size", label: "Biggest", column: "Size" },
];

type Sortable = { rank: number; raw: Record<string, number> };

export function sortParks<T extends Sortable>(parks: T[], key: SortKey): T[] {
  const byRank = (a: T, b: T) => a.rank - b.rank;
  if (key === "score") return [...parks].sort(byRank);
  return [...parks].sort((a, b) => (b.raw[key] ?? 0) - (a.raw[key] ?? 0) || byRank(a, b));
}

const fold = (s: string) =>
  s.normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/['’`]/g, "").toLowerCase();

export function matchesName(name: string, query: string): boolean {
  const q = fold(query).trim();
  return q === "" || fold(name).includes(q);
}

const units: Record<string, [string, string]> = {
  play: ["piece", "pieces"], seating: ["seat/table", "seats/tables"], bbq: ["barbecue", "barbecues"],
  water: ["tap/shower", "taps/showers"], sport: ["field", "fields"],
};

export function formatFactor(key: string, v: number): string {
  if (key === "dogs") return v ? "Yes" : "No";
  if (key === "trees") return `${Math.round(v)} per ha`;
  if (key === "size") return `${v.toFixed(1)} ha`;
  const [one, many] = units[key] ?? ["", ""];
  return `${v} ${v === 1 ? one : many}`.trim();
}
