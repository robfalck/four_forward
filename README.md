# Four Forward

Four Forward is a retro side-scrolling lunar lander game with fluorescent-green vector graphics, inspired by 1970s/80s arcade aesthetics.

Land on as many pads as you can while conserving fuel. Your score is the fuel remaining when you touch down.

---

## Requirements

Runs on **Windows**, **macOS** (Apple Silicon and Intel) and **Linux** (x86-64). You need:

- [git](https://git-scm.com/downloads) — to download the game.
- [pixi](https://pixi.sh) — installs Python and everything else the game needs, automatically.
  - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | iex"`
  - macOS / Linux: `curl -fsSL https://pixi.sh/install.sh | sh`

  Close and reopen your terminal after installing pixi.

---

## Installation

```bash
git clone https://github.com/robfalck/four_forward.git
cd four_forward
```

---

## Running the game

```bash
pixi run python -m four_forward
```

The first run downloads Python and the game's dependencies, which takes a few minutes.
After that it starts in a few seconds.

To get the latest version later, run `git pull` inside the `four_forward` folder.

---

## Controls

### Flight

| Key / Input | Action |
|---|---|
| `Space` | Fire main thruster (full throttle) |
| `A` | Rotate left (nose left / CCW) |
| `D` | Rotate right (nose right / CW) |
| Left mouse button (drag) | Steer — drag left or right to rotate |
| Joystick left stick X | Rotate |
| Joystick left stick Y | Throttle (pull back to thrust) |

### Game flow

| Key | Action |
|---|---|
| `Space` | Launch from the Ready for Launch screen |
| `Up` / `Down` (or `W` / `S`), `Enter` | Choose difficulty (menu after the title screen) |
| `1` / `2` / `3` | Select Easy / Medium / Hard (difficulty menu or Ready for Launch screen) |
| `N` | Generate new terrain (Ready for Launch screen) |
| `R` | Restart with new terrain (after landing or crash) |
| `L` | View leaderboard (title screen, difficulty menu, or Ready for Launch screen) |
| `-` / `=` | Chatter volume down / up (any time); or drag the VOL slider (not while flying) |
| `Esc` | Quit |

---

## Gameplay

- You begin at 10 km altitude with a random velocity and flight path angle. The ground will not be visible until you descend close enough for it to enter the field of view — the camera zooms in automatically as you approach.
- Four landing pads are scattered across the terrain. Land on one to score.
- Safe landing thresholds: vertical speed ≤ 10 m/s, horizontal speed ≤ 6 m/s, tilt ≤ 15°.
- Difficulty sets the pad width and the safe vertical speed:

  | Difficulty | Pad width | Safe vertical speed |
  |---|---|---|
  | Easy | 600 m | 15 m/s |
  | Medium (default) | 300 m | 10 m/s |
  | Hard | 225 m | 10 m/s |
- Your score is based on a successful landing:

  **score = fuel left (kg) × difficulty × pad × speed**

  | Bonus | Values |
  |---|---|
  | Difficulty | Easy ×1, Medium ×1.5, Hard ×2 |
  | Pad (counted left to right) | 1st ×1, 2nd ×1.25, 3rd ×1.5, 4th ×1.75 |
  | Speed (launch to touchdown) | ×1.5 at 2 min or faster, sliding to ×0.75 at 6 min or slower |

  The touchdown screen shows the full breakdown.
- After a successful landing you're asked for a name. Scores go on this computer's top ten
  and, if it's set up, the **worldwide** top ten (one entry per computer, its best score).
  Press `L` on the title screen (or any pre-launch screen) to see both. Setting up the worldwide board:
  see [`supabase/README.md`](supabase/README.md).
- Drifting left past the visible area counts as a loss.

---

## Development

Lint:

```bash
pixi run --environment dev ruff check src/
```
