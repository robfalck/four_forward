# FOUR FORWARD — Development Log

Decisions are recorded in reverse-chronological order (newest first).

---

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
