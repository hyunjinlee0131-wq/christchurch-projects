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
