# FOUR FORWARD — Development Log

Decisions are recorded in reverse-chronological order (newest first).

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
