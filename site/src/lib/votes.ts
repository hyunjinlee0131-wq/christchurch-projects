// Park votes and 👍/👎 feedback via Supabase's REST API (no SDK).
// The database only lets anonymous users insert rows and read the vote-count view (insert-only RLS).
export type Config = { url: string; key: string };
export type Result = { ok: boolean; already?: boolean; error?: string };

const ENV: Config = {
  url: (import.meta.env.PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, ""),
  key: import.meta.env.PUBLIC_SUPABASE_ANON_KEY ?? "",
};
const TIMEOUT_MS = 5000;
const VOTER_KEY = "cp_voter_id";
const VOTED_KEY = "cp_voted";
let memoryVoterId: string | null = null;

export function votingEnabled(cfg: Config = ENV): boolean {
  return Boolean(cfg.url && cfg.key);
}

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function safeStorage(): Storage | undefined {
  try {
    return typeof localStorage === "undefined" ? undefined : localStorage;
  } catch {
    return undefined;
  }
}

export function getVoterId(storage: Storage | undefined = safeStorage()): string {
  try {
    const existing = storage?.getItem(VOTER_KEY);
    if (existing) return existing;
    const id = memoryVoterId ?? uuid();
    storage?.setItem(VOTER_KEY, id);
    memoryVoterId = id;
    return id;
  } catch {
    // Private mode / blocked storage: keep one id for this page session.
    return (memoryVoterId ??= uuid());
  }
}

export function votedParks(storage: Storage | undefined = safeStorage()): Set<string> {
  try {
    return new Set(JSON.parse(storage?.getItem(VOTED_KEY) ?? "[]"));
  } catch {
    return new Set();
  }
}

export function rememberVote(parkId: string, storage: Storage | undefined = safeStorage()): void {
  try {
    const s = votedParks(storage);
    s.add(parkId);
    storage?.setItem(VOTED_KEY, JSON.stringify([...s]));
  } catch {
    /* not fatal: the database's unique key still prevents double votes */
  }
}

async function request(path: string, init: RequestInit, f: typeof fetch, cfg: Config): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    return await f(`${cfg.url}/rest/v1/${path}`, {
      ...init,
      signal: ctrl.signal,
      headers: { apikey: cfg.key, Authorization: `Bearer ${cfg.key}`, "Content-Type": "application/json",
                 Prefer: "return=minimal", ...(init.headers as Record<string, string> | undefined) },
    });
  } finally {
    clearTimeout(timer);
  }
}

async function insert(table: string, row: object, f: typeof fetch, cfg: Config): Promise<Result> {
  if (!votingEnabled(cfg)) return { ok: false, error: "not configured" };
  try {
    const r = await request(table, { method: "POST", body: JSON.stringify(row) }, f, cfg);
    if (r.status === 201 || r.status === 204) return { ok: true };
    if (r.status === 409) return { ok: true, already: true };
    return { ok: false, error: `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) };
  }
}

export function castVote(parkId: string, voterId: string = getVoterId(), f: typeof fetch = fetch, cfg: Config = ENV) {
  return insert("park_votes", { park_id: parkId, voter_id: voterId }, f, cfg);
}

export function sendFeedback(project: string, itemId: string, value: 1 | -1, voterId: string = getVoterId(),
                             f: typeof fetch = fetch, cfg: Config = ENV) {
  return insert("feedback", { project, item_id: itemId, value, voter_id: voterId }, f, cfg);
}

export async function getCounts(f: typeof fetch = fetch, cfg: Config = ENV): Promise<Record<string, number> | null> {
  if (!votingEnabled(cfg)) return null;
  try {
    const r = await request("park_vote_counts?select=park_id,votes", { method: "GET" }, f, cfg);
    if (!r.ok) return null;
    const rows = (await r.json()) as { park_id: string; votes: number }[];
    return Object.fromEntries(rows.map((x) => [x.park_id, Number(x.votes)]));
  } catch {
    return null;
  }
}
