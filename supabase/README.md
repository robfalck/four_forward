# Worldwide leaderboard setup (Supabase)

The game reads and writes a shared top-ten list stored in a free Supabase project.
Until `WORLD_LEADERBOARD_URL` and `WORLD_LEADERBOARD_KEY` in
`src/four_forward/constants.py` are filled in, the worldwide leaderboard is simply
switched off and the game works as before.

## One-time setup

1. Create a free account at <https://supabase.com> and click **New project**.
   Any name and region is fine; save the database password somewhere (the game
   doesn't need it).
2. When the project is ready, open **SQL Editor → New query**, paste the whole of
   [`leaderboard.sql`](leaderboard.sql), and click **Run**. It should report success.
3. Open **Project Settings → API** (or the **Connect** button) and copy:
   - the **Project URL**, e.g. `https://abcdefghijkl.supabase.co`
   - the **anon / public** API key (a long string starting `eyJ...`, or `sb_publishable_...`)
4. Paste them into `src/four_forward/constants.py`:

   ```python
   WORLD_LEADERBOARD_URL = "https://abcdefghijkl.supabase.co"
   WORLD_LEADERBOARD_KEY = "eyJ..."
   ```

5. Commit and push, so every copy of the game uses the same leaderboard.

## Is it safe to publish the key?

Yes — use the **anon / publishable** key only, never the `service_role` / secret key.
The anon key is designed to be public. The SQL turns on row-level security and only
allows anonymous users to *add* scores; they cannot read the raw table, change or
delete anyone's score. The top ten is read through the `top_scores()` function.

## Limits

- The database rejects impossible scores (outside 0–500 kg of fuel), unknown
  difficulties, and names longer than 16 characters.
- Because the game is open source, someone determined could still send a fake but
  plausible score. To remove one, open **Table Editor → scores** in the dashboard
  and delete the row.
- Free Supabase projects pause after a week with no activity; un-pause from the
  dashboard if the game starts showing "OFFLINE".
