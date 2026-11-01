import { describe, expect, it } from "vitest";
import { dataVsPeople, peopleRanking } from "../src/lib/people";

const parks = [
  { id: "a", name: "A", rank: 1 }, { id: "b", name: "B", rank: 2 },
  { id: "c", name: "C", rank: 3 }, { id: "d", name: "D", rank: 4 },
];

describe("people's choice", () => {
  it("ranks by votes, ties by data rank, ignores unvoted parks", () => {
    const r = peopleRanking(parks, { c: 5, b: 5, a: 1 });
    expect(r.map((p) => [p.id, p.votes, p.peopleRank])).toEqual([["b", 5, 1], ["c", 5, 2], ["a", 1, 3]]);
  });

  it("data vs people needs a minimum number of votes", () => {
    expect(dataVsPeople(parks, { a: 1 }, 20)).toBeNull();
  });

  it("finds underrated (people rank much better than data) and overrated parks", () => {
    const res = dataVsPeople(parks, { d: 15, c: 4, a: 1 }, 20)!;
    expect(res.underrated[0].id).toBe("d"); // data #4, people #1
    expect(res.overrated[0].id).toBe("a"); // data #1, people #3
  });
});

describe("data vs people threshold", () => {
  it("ignores votes for ids that aren't real parks", () => {
    expect(dataVsPeople(parks, { "9999999": 30, a: 1 }, 20)).toBeNull();
  });
});

import { podium } from "../src/lib/people";

describe("podium", () => {
  const ranked = peopleRanking(
    [1, 2, 3, 4, 5, 6].map((i) => ({ id: String(i), name: `P${i}`, rank: i })),
    { "1": 9, "2": 8, "3": 7, "4": 6, "5": 5, "6": 4 },
  );
  it("splits the top 5 into a top 3 and two runners-up", () => {
    const { top3, runnersUp } = podium(ranked);
    expect(top3.map((p) => p.id)).toEqual(["1", "2", "3"]);
    expect(runnersUp.map((p) => p.id)).toEqual(["4", "5"]);
  });
  it("copes with fewer than 5 voted parks", () => {
    const { top3, runnersUp } = podium(ranked.slice(0, 2));
    expect(top3.length).toBe(2);
    expect(runnersUp).toEqual([]);
  });
});
