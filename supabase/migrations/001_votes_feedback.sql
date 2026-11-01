-- Christchurch Projects: park votes + 👍/👎 feedback.
-- Run once in the Supabase SQL editor. Anonymous visitors can only INSERT rows and read vote totals.
-- This is a deliberate, limited defence: it cannot stop a determined cheater (design §7.1).

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.park_votes (
  park_id    text not null check (char_length(park_id) between 1 and 64),
  voter_id   uuid not null,
  ip_hash    text,
  created_at timestamptz not null default now(),
  primary key (park_id, voter_id)          -- one vote per park per browser; repeats return HTTP 409
);

create table if not exists public.feedback (
  project    text not null check (char_length(project) between 1 and 64),
  item_id    text check (char_length(item_id) <= 128),
  value      smallint not null check (value in (-1, 1)),
  voter_id   uuid,
  ip_hash    text,
  created_at timestamptz not null default now()
);

-- Row-level security: insert only. No select/update/delete policies exist, so those are denied.
alter table public.park_votes enable row level security;
alter table public.feedback   enable row level security;

drop policy if exists "anon can vote" on public.park_votes;
create policy "anon can vote" on public.park_votes for insert to anon with check (true);

drop policy if exists "anon can give feedback" on public.feedback;
create policy "anon can give feedback" on public.feedback for insert to anon with check (true);

revoke all on public.park_votes, public.feedback from anon;
grant insert (park_id, voter_id) on public.park_votes to anon;
grant insert (project, item_id, value, voter_id) on public.feedback to anon;

-- Totals only (no voter ids or hashes). The view runs with its owner's rights, so it can count rows anon can't read.
create or replace view public.park_vote_counts as
  select park_id, count(*)::int as votes from public.park_votes group by park_id;
revoke all on public.park_vote_counts from anon;
grant select on public.park_vote_counts to anon;

-- Rate limit: hash the caller's IP (never stored raw) and cap inserts per IP per 10 minutes.
create or replace function public.limit_inserts() returns trigger
language plpgsql security definer set search_path = public, extensions as $$
declare
  ip text := split_part(coalesce(current_setting('request.headers', true)::json->>'x-forwarded-for', ''), ',', 1);
  recent int;
  max_per_10min int := case when tg_table_name = 'park_votes' then 30 else 20 end;
begin
  new.ip_hash := encode(digest(ip, 'sha256'), 'hex');
  new.created_at := now();
  execute format('select count(*) from public.%I where ip_hash = $1 and created_at > now() - interval ''10 minutes''', tg_table_name)
    into recent using new.ip_hash;
  if recent >= max_per_10min then
    raise exception 'rate limit: too many submissions, try again later' using errcode = 'P0001';
  end if;
  return new;
end $$;

drop trigger if exists limit_votes on public.park_votes;
create trigger limit_votes before insert on public.park_votes for each row execute function public.limit_inserts();

drop trigger if exists limit_feedback on public.feedback;
create trigger limit_feedback before insert on public.feedback for each row execute function public.limit_inserts();

create index if not exists park_votes_ip_recent on public.park_votes (ip_hash, created_at);
create index if not exists feedback_ip_recent   on public.feedback (ip_hash, created_at);
