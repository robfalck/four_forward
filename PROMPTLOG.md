# Four Forward — Prompt Log

A running record of development conversations. Newest entries at the top.
Each session captures the key prompts and what was decided or learned.

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
