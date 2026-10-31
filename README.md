# Four Forward

Four Forward is a retro side-scrolling lunar lander game with fluorescent-green vector graphics, inspired by 1970s/80s arcade aesthetics.

Land on as many pads as you can while conserving fuel. Your score is the fuel remaining when you touch down.

---

## Requirements

- [pixi](https://prefix.dev/docs/pixi/overview) — manages Python and all dependencies automatically.

---

## Installation

```bash
git clone <repo-url>
cd four_forward.git
pixi install
```

---

## Running the game

```bash
pixi run python -m four_forward
```

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
| `L` | View leaderboard (Ready for Launch screen) |
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
- Your score is the fuel remaining (kg) at touchdown — conserve it.
- Drifting left past the visible area counts as a loss.

---

## Development

Lint:

```bash
pixi run --environment dev ruff check src/
```
