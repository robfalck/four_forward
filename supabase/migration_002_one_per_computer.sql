-- Migration 002: one leaderboard entry per computer instead of per player name.
-- For databases created from an earlier leaderboard.sql. Run once in the Supabase
-- SQL Editor, BEFORE releasing a game version that sends device_id.

alter table public.scores
    add column if not exists device_id text check (device_id ~ '^[0-9a-f]{32}$');

-- Top n computers, one row per device_id using its best score; rows without a
-- device_id (very old clients) are grouped by player name. Earlier submissions win ties.
create or replace function public.top_scores(n int default 10)
returns table (name text, score real, difficulty text, created_at timestamptz)
language sql
stable
security definer
set search_path = public
as $$
    select name, score, difficulty, created_at
    from (
        select distinct on (coalesce(device_id, 'name:' || lower(btrim(name))))
               btrim(name) as name, score, difficulty, created_at
        from scores
        order by coalesce(device_id, 'name:' || lower(btrim(name))), score desc, created_at
    ) best
    order by score desc, created_at
    limit least(greatest(n, 1), 50);
$$;

grant execute on function public.top_scores(int) to anon;
