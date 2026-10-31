# Four Forward — Prompt Log

A running record of development conversations. Newest entries at the top.
Each session captures the key prompts and what was decided or learned.

---

## 2026-10-31 — Credit line

**Prompts:**

> "remove robert from the credits"

**What was decided:**
- Bottom-right credit now reads "WYATT Falck".

---

## 2026-10-30 — Volume slider, credit, Claude's run

**Prompts:**

> "you do a run and put your score on the leaderboard under the name CLAUDE"
>
> "make a volume slider that can change the volume of the chatter and put WYATT/ROBERT Falck on the bottom right of the screen at all times"
>
> "commit and push when done and then show the results"

**What was decided:**
- Claude flew a real game via an autopilot and landed on HARD with 226.7 kg of fuel. It is
  #2 worldwide, behind john at 288.2 kg on EASY, and submitted as its own "computer".
- Added a VOL slider (mouse + `-`/`=` keys, saved between sessions).
- Added a permanent "WYATT/ROBERT Falck" credit, bottom-right.

---

## 2026-10-30 — One world-leaderboard entry per computer

**Prompts:**

> "ive played two games on this computer and they both went to the world leaderboard and it should be one per computer"

**What was decided:**
- Random per-computer ID sent with each score; world top ten shows each computer's best.
- Migration SQL for the existing database plus a one-off UPDATE for the two existing rows.

---

## 2026-10-30 — Leaderboard from start; quieter chatter ambience

**Prompts:**

> "let me open the leaderboard off rip i currently have to play a game to be able to see it"
>
> "and make the background noise quiter and more like chatter not just radio"

**What was decided:**
- `L` works from the title screen and difficulty menu; back returns to where you were.
- Leaderboard gets its own clean background.
- Replaced the static-hiss loop with a 44 s crew-chatter loop built by a new tool,
  about 11 dB quieter.

---

## 2026-10-30 — Sharing with friends; Mac and Linux

**Prompts:**

> "how do i search it up and find it in github like if i want one of my friends to play it"
>
> "mac and linux puch and commit"

**What was decided:**
- Share the direct link (github.com/robfalck/four_forward); new repos are slow to appear in search.
- Added macOS/Linux pixi platforms and fixed the README install steps.

---

## 2026-10-30 — Public repo and worldwide leaderboard

**Prompts:**

> "make it public and then also people's high scores that were done on other computers can those be put on a worldwide leaderboard that shows the top ten people"

**What was decided:**
- Scanned history for secrets (none), then made the GitHub repo public.
- Backend: Supabase (user's choice), insert-only from the game, top ten read via an SQL function.
- Top ten shows one entry per player (their best score), tagged with difficulty.
- The board is off until the Supabase URL and anon key are pasted into `constants.py`
  (steps in `supabase/README.md`).

---

## 2026-10-30 — Leaderboard difficulty tag

**Prompts:**

> "make it so there is a tag of which difficulty was used on the leaderboard then commit"

**What was decided:**
- Store and display the difficulty with every score; legacy scores default to MEDIUM.

---

## 2026-10-30 — Difficulty menu

**Prompts:**

> "i was not given a menu to choose my difficulty so i need one of those"
>
> "put it after press any key to start"

**What was decided:**
- Added a dedicated difficulty menu screen right after the "press any key" splash.
- Fixed the held-Space launch skip and the pre-launch camera framing found while testing.

---

## 2026-10-30 — Difficulty levels

**Prompts:**

> "now make it so that you can pick difficulties easy medium and hard where medium is the size of pads that they are right now easy makes them twice as big and makes the safe speed 15 units and hard makes it twenty five percent smaller than original"

**What was decided:**
- EASY: 600 m pads, 15 m/s safe speed. MEDIUM: 300 m, 10 m/s. HARD: 225 m, 10 m/s
  (safe speed for Hard was not specified, so it keeps the original 10 m/s).
- Keys 1/2/3 select difficulty on the setup screen. The selection is shown there and in the HUD.
- Pads are now stored in metres so non-step-multiple widths are exact.

---

## 2026-10-30 — Land on the foot pads, not the lander centre

**Prompts:**

> "I want to make so that when the bottom of the lander touches the ground that is when it considers it landed instead of when it hits the middle"

**What was decided:**
- Root cause: the drawn lander used a minimum pixel scale (28 px/unit) larger than the world
  scale assumed by collision, so the 40 m foot offset sat roughly mid-body on screen.
- Introduced a shared `LANDER_DRAW_SCALE_M` for both rendering and collision.
- Collision now uses the rotated bottom of each foot pad against the terrain beneath it.

---

## 2026-03-23 — Audio / Sound Design Research

**Context:** Planning ambient background audio using Apollo landing recordings.

**Prompts:**

> "I would like to have sort of a constant droning sound taken from audio clips from the apollo landing as the 'background sound' that is constant. If I have an mp3, how do I take a section of it and loop it infinitely?"

**What was decided:**
- Use `ffmpeg` to trim a clip (`-ss`, `-to` / `-t` flags).
- Prefer `.ogg` or `.wav` over `.mp3` for pygame reliability.
- Loop with `pygame.mixer.music.play(loops=-1)`.
- Store audio in `assets/` directory, reference path via `constants.py`.

---

> "Are there any audio tools that I can train on the sound and have them make a simulated loop that's close?"

**What was learned / options surfaced:**
- **ElevenLabs Sound Effects** — text-to-sound, free tier, good for ambient drones.
  - Suggested prompt: `"Apollo lunar module descent engine drone, constant low frequency rumble"`
- **Stable Audio** (Stability AI) — text-to-audio, good for ambient textures, specifiable duration.
- **AudioCraft / AudioGen** (Meta, open source) — can do "continuation" mode: feed a few seconds of real audio and it extends it in the same texture. Most control.
- **UDIO** — music-focused but handles drone/ambient; accepts reference clip.
- **Loopify** (loopify.app) — browser tool that auto-detects seamless loop points in an existing clip. No AI needed.

**Recommendation recorded:** Try ElevenLabs first (fast, free), fall back to AudioCraft continuation mode on an actual Apollo clip if needed.

---

<!-- Add new entries above this line -->
