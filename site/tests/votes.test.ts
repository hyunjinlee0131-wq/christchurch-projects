import { describe, expect, it, vi } from "vitest";
import { castVote, getCounts, getVoterId, sendFeedback, votingEnabled } from "../src/lib/votes";

const CFG = { url: "https://abc.supabase.co", key: "anon-key" };
const res = (status: number, body: unknown = null) =>
  Promise.resolve(new Response(body === null ? null : JSON.stringify(body), { status }));

function memStorage(): Storage {
  const m = new Map<string, string>();
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, v), removeItem: (k) => void m.delete(k),
           clear: () => m.clear(), key: () => null, get length() { return m.size; } } as Storage;
}

describe("vote client", () => {
  it("201 ok, posts to park_votes with anon headers", async () => {
    const f = vi.fn(() => res(201));
    expect(await castVote("P1", "voter-1", f as any, CFG)).toEqual({ ok: true });
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("https://abc.supabase.co/rest/v1/park_votes");
    expect((init.headers as Record<string, string>).apikey).toBe("anon-key");
    expect(JSON.parse(init.body as string)).toEqual({ park_id: "P1", voter_id: "voter-1" });
  });

  it("409 counts as already voted", async () => {
    expect(await castVote("P1", "v", (() => res(409)) as any, CFG)).toEqual({ ok: true, already: true });
  });

  it("unreachable server returns {ok:false}", async () => {
    const r = await castVote("P1", "v", (() => Promise.reject(new TypeError("Failed to fetch"))) as any, CFG);
    expect(r.ok).toBe(false);
    expect(r.error).toBeTruthy();
  });

  it("5xx returns {ok:false}", async () => {
    expect((await castVote("P1", "v", (() => res(503)) as any, CFG)).ok).toBe(false);
  });

  it("aborts after the timeout", async () => {
    vi.useFakeTimers();
    const f = (_u: string, init: RequestInit) =>
      new Promise<Response>((_, reject) => init.signal!.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError"))));
    const p = castVote("P1", "v", f as any, CFG);
    await vi.advanceTimersByTimeAsync(5001);
    expect((await p).ok).toBe(false);
    vi.useRealTimers();
  });

  it("disabled config returns {ok:false} without calling fetch", async () => {
    const f = vi.fn();
    expect((await castVote("P1", "v", f as any, { url: "", key: "" })).ok).toBe(false);
    expect(f).not.toHaveBeenCalled();
  });
});

describe("counts and feedback", () => {
  it("getCounts maps rows to a record", async () => {
    const f = () => res(200, [{ park_id: "P1", votes: 3 }, { park_id: "P2", votes: 1 }]);
    expect(await getCounts(f as any, CFG)).toEqual({ P1: 3, P2: 1 });
  });

  it("getCounts returns null on 500", async () => {
    expect(await getCounts((() => res(500)) as any, CFG)).toBeNull();
  });

  it("sendFeedback posts value", async () => {
    const f = vi.fn(() => res(201));
    expect((await sendFeedback("best_park", "ranking", 1, "v", f as any, CFG)).ok).toBe(true);
    const [, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ project: "best_park", item_id: "ranking", value: 1, voter_id: "v" });
  });
});

describe("voter id", () => {
  it("persists in storage", () => {
    const s = memStorage();
    const a = getVoterId(s);
    expect(a).toMatch(/^[0-9a-f-]{36}$/);
    expect(getVoterId(s)).toBe(a);
  });

  it("falls back when localStorage throws", () => {
    const broken = { getItem: () => { throw new Error("denied"); }, setItem: () => { throw new Error("denied"); } } as unknown as Storage;
    const a = getVoterId(broken);
    expect(a).toMatch(/^[0-9a-f-]{36}$/);
    expect(getVoterId(broken)).toBe(a); // stable for the session
  });

  it("votingEnabled false without env", () => {
    expect(votingEnabled({ url: "", key: "" })).toBe(false);
    expect(votingEnabled(CFG)).toBe(true);
  });
});
