# FOUR FORWARD — Development Log

Decisions are recorded in reverse-chronological order (newest first).

---

## 2026-10-30 — Volume slider, credit line, CLAUDE autopilot run

### Volume slider
- VOL slider under the minimap on every screen except the splash. `-`/`=` (and keypad)
  adjust in 5% steps at any time except the name prompt (where they are typed characters).
- Mouse dragging is disabled while flying, because a left-drag already steers the lander.
- New `settings.py` saves the volume to `~/.four_forward_settings.json`;
  `AMBIENT_VOLUME` is now only the first-run default.
- `VOLUME_SLIDER_RECT` lives in `renderer.py` and `game.py` uses the same rect for mouse
  hits, so drawing and hit-testing can't drift apart.

### Credit
- "WYATT/ROBERT Falck" is drawn bottom-right on every screen, including the splash and
  leaderboard, on a small dark backing so it reads over the bright splash art. The compact
  post-landing leaderboard moved up 20 px to clear it.

### CLAUDE's leaderboard run
- Flown by an autopilot through the game's real interface (`Lander.update` throttle/torque,
  `_check_collision`, name entry and `WorldLeaderboard.submit`). It is not a hand-typed score.
- Guidance: ZEM/ZEV energy-optimal guidance to a waypoint 60 m above the pad, then a
  terminal descent controller; PD attitude control matched to θ'' = 2·cmd − ω. It plans by
  simulating 8 approach times × 4 pads and flies the most fuel-efficient one that lands.
- Result: HARD, seed 1793417274, second pad (48 km), 211.5 s flight, touchdown at
  2.2 m/s vertical and 0.1 m/s horizontal, 226.7 kg fuel. Submitted under a separate
  device ID so it doesn't displace the dev machine's entry. The script stays in the session
  scratchpad and is not committed.

---

## 2026-10-30 — Worldwide leaderboard: one entry per computer

- The world board grouped by player name, so one person typing different names took several
  spots. Now each game install sends a random `device_id` (uuid4 hex, stored in
  `~/.four_forward_device_id`) and `top_scores()` keeps the best score per `device_id`,
  shown under the name used for that score.
- Rows without a `device_id` (clients from before this change) still group by name, via
  `coalesce(device_id, 'name:' || lower(name))`.
- `device_id` is client-supplied, so it is a fairness default, not anti-cheat: deleting the
  file or editing the code gives a new ID.
- Schema change shipped as `supabase/migration_002_one_per_computer.sql`; `leaderboard.sql`
  is updated for fresh setups. The migration must run before the client that sends
  `device_id` is pushed, otherwise PostgREST rejects inserts with an unknown column.
- The two rows already on the board (both from the dev machine) were tagged with that
  machine's ID by a one-off UPDATE run in the dashboard (not committed).

---

## 2026-10-30 — Leaderboard from the title screen; chatter ambience

### Leaderboard access
- `L` now opens the leaderboard from the splash screen and the difficulty menu as well as
  setup. `_open_leaderboard()` records the screen it came from (`_leaderboard_return`) so
  "any key" goes back there instead of always to setup.
- The leaderboard is now a standalone screen (starfield only). It used to be drawn over the
  live scene, so the HUD, lander, minimap and a second hint line showed through it.

### Ambient audio
- The old loop came from `find_loop.py`, which picks the *steadiest* stretch of a recording.
  In practice that was 7 s of pure radio static (0% speech frames, −14.5 dBFS RMS).
- New `tools/make_chatter_loop.py` does the opposite: it picks the 45 s window with the most
  continuous voice activity, snaps both ends to quiet frames so no word is cut, applies a
  gentle compressor so loud transmissions don't jump out, normalises to −26 dBFS, and
  equal-power crossfades the seam. Output is mono 22.05 kHz (240 KB).
- Source: NASA Apollo 11 onboard audio highlight clip 3 (public domain), 122.5–168.1 s.
  The result is ~33% speech frames and ~11 dB quieter than the old loop. `AMBIENT_VOLUME`
  is unchanged and is the knob for further tuning.
- libsndfile overflows its stack on Windows when writing a long Vorbis stream in one call,
  so the tool writes in 8192-sample blocks.

---

## 2026-10-30 — macOS and Linux support

- Added `linux-64`, `osx-arm64` and `osx-64` to the pixi workspace platforms and re-locked.
  Windows pins are unchanged (jax/jaxlib 0.9.2, pygame-ce 2.5.7).
- Intel macOS resolves to jax/jaxlib 0.4.38, the last release with Intel-Mac wheels. That
  still satisfies `jax>=0.4.30` and everything the game uses (`jax.config`, `.at[]`, jit).
  Other new platforms get jax 0.12.
- Not run on macOS or Linux yet; the lockfile solve confirms wheels exist for each platform.
- README: real clone URL, correct folder name (`four_forward`), pixi install commands.

---

## 2026-10-30 — Worldwide leaderboard (Supabase)

### Backend choice
- Supabase (hosted Postgres + auto-generated REST API) over a custom Cloudflare Worker or
  dreamlo: no server code to maintain, and its public "anon" key can safely ship in an
  open-source client because row-level security limits it. dreamlo would have required
  publishing a key that can wipe the board.
- `supabase/leaderboard.sql`: `scores` table with CHECK constraints (name 1–16 chars,
  score 0–500 kg = FUEL_MASS, difficulty in EASY/MEDIUM/HARD), RLS with an INSERT-only
  policy, and a `security definer` function `top_scores(n)` that returns each player's
  best score (`distinct on lower(btrim(name))`). The raw table is not readable by anon.
- Cheating cannot be fully prevented with an open-source client; constraints only reject
  impossible values. Bad rows are removed by hand in the dashboard.

### Client
- `world_leaderboard.py` uses stdlib `urllib` on daemon threads, so no new dependency and
  the game loop never blocks. State (`status`, `submit_status`, `entries`) is plain
  attributes that the renderer polls each frame.
- Disabled (no network calls at all) while `WORLD_LEADERBOARD_URL`/`KEY` in `constants.py`
  are blank.
- Threads and urllib won't work under pygbag in the browser; the web port will need a
  `fetch`-based variant of `_post`.

### Game flow
- The name prompt now appears on every successful landing when the world board is enabled
  (heading "SUCCESSFUL LANDING!" unless it is also a local high score). It is pre-filled
  with the last name used. The local board is only updated when the score qualifies.
- The full-screen leaderboard (L) shows "THIS COMPUTER" and "WORLDWIDE" columns and
  refreshes the worldwide list on open. Landed overlay shows the send status.
- Fixed: Esc on the name prompt quit the game because `InputHandler` maps Esc to quit and
  the loop broke before name entry saw it. Esc now skips the prompt; closing the window
  still quits.

---

## 2026-10-30 — Difficulty tag on leaderboard entries

- Each leaderboard entry now stores `difficulty` (the preset name) next to `name`/`score`,
  and both the in-game and full-screen leaderboards show it.
- Entries saved before difficulty levels existed load as MEDIUM, because they were
  played with the original 300 m pads and 10 m/s rules.
- All levels still share one ranked list. The tag makes scores comparable at a glance
  without splitting the leaderboard.
- The compact leaderboard is now right-aligned from its widest row; the fixed 230 px offset
  already let long rows run off the screen edge.

---

## 2026-10-30 — Difficulty menu after the title screen

- New `difficulty` state between `splash` and `setup`: a boxed SELECT DIFFICULTY menu
  (Up/Down or W/S + Enter/Space, or 1/2/3 to pick directly). The cursor writes straight to
  `Game._difficulty`; terrain is only rebuilt on confirm.
- Launch from `setup` now needs a fresh thrust press (`_prev_throttle == 0`). Before this,
  pressing Space to leave the splash screen skipped the setup screen entirely, because Space
  was still held on the next frame, so the player never saw the difficulty selector.
- `_new_game` now calls `camera.track` so the lander is framed before launch. Previously the
  camera sat at y = 0 until the first `playing` frame, so the pre-launch screens showed bare
  terrain with the lander off-screen.

---

## 2026-10-30 — Easy / Medium / Hard difficulty

### Difficulty presets
- New `difficulty.py` with a frozen `Difficulty` dataclass (`pad_width`, `safe_vert_speed`)
  and three presets: EASY (2× pads, 15 m/s), MEDIUM (original 300 m pads, 10 m/s),
  HARD (pads 25% smaller = 225 m, 10 m/s). Kept out of `constants.py` because the presets
  are derived from `PAD_WIDTH` / `SAFE_VERT_SPEED` rather than being independent tunables.
- Selected with 1/2/3 on the Ready for Launch screen. Switching difficulty rebuilds the game
  with the same seed, so the terrain and starting conditions stay identical and only the
  pads change. The choice persists across restarts.

### Pads stored as world-space extents
- 225 m is not a multiple of `TERRAIN_STEP` (50 m), so `Terrain.pads` now holds
  `(x_start, x_end)` in metres instead of sample indices. Every sample spanning the pad is
  flattened so the pad surface is level edge to edge.
- `is_on_pad` is now an exact `x0 <= x <= x1` test. Previously the `int(x / step)` index
  test accepted up to one extra step (50 m) past the right edge, so Medium is very slightly
  stricter than before.

---

## 2026-10-30 — Touchdown detected at the bottom of the foot pads

### Collision geometry now matches the drawn lander
The renderer's 28 px minimum art scale overrode `camera.zoom * LANDER_ART_SCALE_M` (≈12.8 px
at the fixed 5 km field of view), so the lander was drawn ~2.2× larger than the 40 m foot
offset used by collision. Touchdown therefore fired with the drawn lander half-sunk in the
ground. `LANDER_DRAW_SCALE_M = max(LANDER_MIN_PX / ZOOM_FIXED, LANDER_ART_SCALE_M)` is now the
single world-metres-per-art-unit scale used by both the renderer and collision, and
`LANDER_GROUND_OFFSET_M` is derived from it (foot-pad centre + pad radius).

### Per-foot, attitude-aware contact
- Foot-pad geometry (`LANDER_FOOT_X/Y/R_ART`) moved to `constants.py`; the renderer and
  `Lander.foot_contacts()` share it.
- `foot_contacts()` rotates each foot by `theta` exactly as the renderer does, so a tilted
  lander touches down on its low foot first.
- Collision compares each contact point against the terrain height *under that point*,
  not under the lander centre. The body centre is also checked as a fallback for an
  inverted lander.
- On a successful landing the lander is raised by the penetration depth so the pads rest
  exactly on the surface.

---

## 2026-03-21 — Larger lander sprite, redesigned Apollo LM art, parabolic trajectory minimap

### Larger minimum lander size
`_LANDER_MIN_PX` raised from 12 → 28 px. At 10 km altitude the lander is now clearly visible
as a recognisable silhouette rather than a tiny dot. The zoom-adaptive formula
`scale = max(_LANDER_MIN_PX, camera.zoom * LANDER_ART_SCALE_M)` still lets it scale with
zoom; the larger floor just ensures readability at the initial high-altitude view.

### Redesigned Apollo LM silhouette (second pass)
Key changes from the octagonal-stage version:
- **Descent stage**: now hexagonal (6-sided polygon) with chamfered lower corners, matching the
  boxy-but-angled real LM shape. Equipment-bay dividers (two vertical lines) and a horizontal
  seam break up the stage visually.
- **Windows**: trapezoidal (wider at top), matching the real LM triangular window panels.
  Left window: `[(-0.20,0.11),(-0.04,0.11),(-0.07,0.26),(-0.17,0.26)]`.
  Right window: `[(0.04,0.11),(0.20,0.11),(0.17,0.26),(0.07,0.26)]`.
- **Engine nozzle**: flared bell (wider exit than throat), drawn as a filled polygon with an
  outline, more realistic than the old trapezoid.
- **Touch probes**: thin vertical lines extending 0.25 units below each foot pad — the real LM
  had 1.73 m probes to signal engine-cutoff 5 seconds before actual contact.
- **RCS pods**: unchanged 3-line L-shape protrusions on each side of the ascent stage.

### Parabolic trajectory arc on minimap
Replaced the dashed vertical landing-point indicator with a full 2D parabolic arc.
`_ballistic_trajectory(lander, terrain, n_pts=40)` samples 41 points along the free-fall
ballistic path and returns `(world_x, world_y)` pairs. The minimap now uses a **dynamic
y-axis**: `y_top = max(max_terrain_h × 1.1, lander.y × 1.05)` so the arc sweeps from the
lander's actual altitude down to the terrain. `screen.set_clip()` confines all minimap
drawing to the minimap rectangle so the arc never bleeds onto the HUD.

---

## 2026-03-21 — Landing height fix, improved Apollo LM, trajectory indicator, approach status

### Lander art scales with zoom; foot pads land on terrain
Introduced `LANDER_GROUND_OFFSET_M = 40 m` and `LANDER_ART_SCALE_M = 50 m`. The `rot()` helper
now uses `scale = max(12 px, zoom * LANDER_ART_SCALE_M)` so the sprite scales with world zoom
instead of being a fixed 40 px blob. Collision fires when `lander.y > terrain_h + GROUND_OFFSET + 2`,
meaning the foot pads (local y = −0.80 → world −40 m) physically touch the terrain before the
collision triggers. Crash explosion re-centred at foot-pad level (`lander.y − GROUND_OFFSET`).

### Improved Apollo LM silhouette
Key changes from the previous triangle-with-legs:
- Octagonal ascent stage (two chamfered top corners)
- Two side-by-side triangular windows (the most recognisable LM feature)
- Docking tunnel (three-line rectangle on top of ascent stage)
- Equipment-bay panel line on descent stage
- RCS thruster pods (small 3-line rectangle protrusion on each side of ascent stage)
- Diagonal cross-member inside each leg truss (primary strut + brace + cross-member + foot pad)
- Antenna with tip dot

### Ballistic trajectory indicator (minimap)
`_ballistic_landing_x()` solves the quadratic `0.5·g·t²  − vy·t − eff_alt = 0` to predict
where the lander will touch down if thrust is cut. Shown as a dashed vertical line on the minimap.
Predictions beyond 10 minutes are suppressed as noise. Uses `LANDER_GROUND_OFFSET_M` for the
effective altitude so the predicted contact matches the physical foot-pad level.

### Approach status in HUD
Two new lines below the fuel bar (shown only in "playing" state):
- `SPEED  X.X  SAFE / FAST` — current downward speed vs 10 m/s threshold, colour-coded
- `PAD  ON COURSE / OFF COURSE` — ballistic prediction compared against pad positions

## 2026-03-21 — Apollo LM sprite, terrain fade, pad-only landing rule, steeper descent

### Apollo LM line art
Replaced the placeholder triangle with a recognisable Apollo Lunar Module silhouette:
descent stage (wide box), ascent stage (narrower box + dome apex), circular window, engine bell (flared nozzle), two leg assemblies each with a primary strut, brace strut, and foot pad, and a short antenna with a tip dot. All geometry is in normalised local coordinates rotated by lander attitude, so it tilts with the craft.

### Landing rule simplified — pad + vertical speed only
Previous rule required horizontal speed ≤ 6 m/s AND attitude ≤ 15° AND vertical ≤ 8 m/s. Users kept crashing on pads when coming in at an angle. New rule: **on pad + vert_speed ≤ 10 m/s → TOUCHDOWN**. Horizontal speed and attitude no longer matter. `SAFE_VERT_SPEED` raised to 10.0 m/s accordingly. `SAFE_HORZ_SPEED` and `SAFE_ANGLE` kept in constants but no longer enforced (may be used for scoring later).

### Steeper initial descent — always downward
`INITIAL_FPA_RANGE` raised from 20° to 45°. FPA now always in range `[-45°, -5°]` (always descending). Previously the lander could start climbing, giving a free altitude buffer. Now it always arrives nose-down with genuine urgency. Speed range unchanged (60–180 m/s).

### Terrain fade-in instead of hard pop (1500–2000 m gate)
Terrain is fully hidden above 2000 m. Between 2000 m and 1500 m it fades in linearly via a pre-allocated `_terrain_surf` surface with `set_alpha()`. Below 1500 m it draws directly to screen. This avoids the jarring "teleport" of terrain snapping into view.

### Minimap viewport rectangle brightened
Changed from `COLOR_GREEN_DIM` to `COLOR_GREEN_MID` so the field-of-view rectangle is legible against the terrain profile.

## 2026-03-21 — Centred camera, minimap, terrain visibility gate, free scroll

### Camera always centred on lander
Reverted `max(self.x, lander_x)` back to `self.x = lander_x`. The no-backscroll constraint made it feel like the game was fighting the player. Freely centred camera is standard for this type of game and lets the player manoeuvre in any direction.

### Left/right crash boundary restored to x < 0 / x > TERRAIN_WIDTH
With a centred camera, `world_x_min` is always behind the lander so it could never trigger. Crash is now simply "flew off the edge of the terrain map."

### Terrain hidden above 2000 m altitude
When `lander.y - terrain.height_at(lander.x) >= 2000 m`, `_draw_terrain()` is skipped entirely. At high altitude the terrain detail is irrelevant and the clean starfield reads better. Terrain reappears as the lander descends through 2000 m.

### Minimap (upper-right, always visible)
A 260×80 px minimap shows:
- Full terrain profile subsampled to one point per pixel column
- Landing pads in bright green
- Camera viewport outline (shows what fraction of the map is visible)
- Lander as a 2-px dot (y clamped to minimap bounds when above terrain height range)

The minimap always draws regardless of altitude so the player always knows their horizontal position and where the pads are. Title text is centred above the minimap rather than floating in the top-right corner.

---

## 2026-03-21 — Setup state, left-edge start, no-backscroll camera, terrain tuning, HUD sign fix

### Setup pre-game state (new)
Added a `"setup"` state that the game starts in before physics begin. The state machine is now `setup → playing → landed | crashed`. From setup, **SPACE** launches and **N / R** regenerates terrain. From landed/crashed, **N / R** also returns to setup. This lets the player survey the terrain and choose a seed before committing to a run.

### Lander starts at the left edge
`lander_x` was moved from `TERRAIN_WIDTH / 2` to `float(2 * TERRAIN_STEP)` (100 m from left). The intent is a pure left-to-right challenge: the player must fly forward, not hover in the middle of the map.

### Camera is monotonically non-decreasing (no backward scroll)
`camera.track()` changed from `self.x = lander_x` to `self.x = max(self.x, lander_x)`. The camera never scrolls left. Combined with the left-edge crash check (below), retreating is fatal. Camera is anchored at the lander's start position on `_new_game()` so the view opens correctly on the left edge of the terrain.

### Left-edge crash boundary
The old `x < 0` out-of-bounds check was replaced with `x < self.camera.world_x_min`. The camera's live left edge (which advances as the player moves right) acts as an invisible wall of death. Flying backward off the left side of the screen → **SPACECRAFT LOST**.

### More mountainous terrain
`TERRAIN_AMPLITUDE` raised from 600 m → 1400 m (taller peaks). Midpoint-displacement roughness decay raised from 0.65 → 0.72 (retains more high-frequency detail → spikier ridges). The earlier terrain felt too flat to be interesting given the 20 km starting altitude.

### HUD vertical speed sign convention
HUD was displaying `lander.vert_speed` (= `-vy`, positive when descending). Changed to `lander.vy` (standard physics sign: negative = descending, positive = ascending). The collision system still uses `vert_speed` internally since it compares against a positive threshold.

---

## 2026-03-21 — Initial game implementation

### Technology choices
- **pygame-ce** over vanilla pygame: maintained fork with better performance and web export support via pygbag.
- **JAX** for the equations of motion: the ODE is written as a pure JAX function so it is JIT-compiled for the game loop and also directly usable by optimal-control solvers (JAX autodiff gives the A/B matrices for free). RK4 integrator is JIT-compiled separately.
- **pixi** for environment management (two envs: `default` for play, `dev` adds ruff + pytest).
- **ruff** (E, F, W, I rule sets) as the sole linter/formatter.

### Physics model
Rectilinear gravity (x/y only), moon gravity 1.62 m/s². Lander starts at 20 km above mean terrain with a random speed (60–180 m/s) and flight-path angle (±20°). Controls: A/D keys rotate via reaction-control torque; SPACE fires main thruster at full throttle. Joystick and mouse-drag axes are also supported and user-remappable.

### Terrain generation
Midpoint displacement (diamond-square in 1-D). Terrain is `TERRAIN_WIDTH = 120 km` wide with `TERRAIN_STEP = 50 m` resolution. `N_PADS = 4` flat landing pads are levelled to the local mean height after generation. Each pad is `300 m` wide.

### Renderer
Retro phosphor-green aesthetic: fluorescent green (`#39ff14`) on black with a scanline CRT overlay. Three brightness levels (full / mid / dim) for foreground, terrain/fx, and stars. Star field has parallax scrolling. Lander is a triangle with landing legs and a randomised thrust flame polygon. Camera has altitude-adaptive zoom (keeps altitude gap at a fixed screen fraction).

### Camera
World-to-screen transform centred on `camera.x, camera.y`. Zoom is clamped between `ZOOM_MIN = 0.01` and `ZOOM_MAX = 0.8` px/m. The lander is kept at 30% from the top of the screen vertically. `world_x_min` / `world_x_max` properties derive the visible world range for terrain culling.

### Safe landing thresholds
Vertical speed ≤ 8 m/s, horizontal speed ≤ 6 m/s, attitude ≤ 15° from vertical, and must be over a pad. All other surface contact is a crash.
