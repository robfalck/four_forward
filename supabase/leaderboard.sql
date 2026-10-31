-- Worldwide leaderboard for Four Forward.
-- Run once in the Supabase dashboard: SQL Editor → New query → paste → Run.
--
-- Security model: the game ships with the public "anon" key, which is safe to
-- publish. With row-level security on and only an INSERT policy, anyone can add
-- a score but nobody can read the raw table, edit or delete rows. Reads go
-- through top_scores(), which returns only each player's best score.

create table if not exists public.scores (
    id          bigint generated always as identity primary key,
    name        text        not null check (char_length(btrim(name)) between 1 and 16),
    -- Score is fuel remaining in kg; the lander starts with 500 kg (FUEL_MASS)
    score       real        not null check (score >= 0 and score <= 500),
    difficulty  text        not null check (difficulty in ('EASY', 'MEDIUM', 'HARD')),
    created_at  timestamptz not null default now()
);

alter table public.scores enable row level security;

drop policy if exists "anyone can submit a score" on public.scores;
create policy "anyone can submit a score"
    on public.scores for insert
    to anon
    with check (true);

grant insert on public.scores to anon;

-- Top n players, one row per player name (case-insensitive) using their best
-- score; earlier submissions win ties.
create or replace function public.top_scores(n int default 10)
returns table (name text, score real, difficulty text, created_at timestamptz)
language sql
stable
security definer
set search_path = public
as $$
    select name, score, difficulty, created_at
    from (
        select distinct on (lower(btrim(name)))
               btrim(name) as name, score, difficulty, created_at
        from scores
        order by lower(btrim(name)), score desc, created_at
    ) best
    order by score desc, created_at
    limit least(greatest(n, 1), 50);
$$;

grant execute on function public.top_scores(int) to anon;
