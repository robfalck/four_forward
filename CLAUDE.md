# Project Info

This is four_forward, a side-scrolling pygame-based video game with retro-looking graphics.

# Session logging

- `PROMPTLOG.md` in the repo root is a running log of development conversations (newest-first).
- **At the end of every session, append a new entry to PROMPTLOG.md** capturing the key prompts used and what was decided or learned.
- Entry format: `## YYYY-MM-DD — short title` followed by the verbatim or paraphrased prompts and a bullet-point summary of outcomes.

# Coding standards

- Make sure code passes ruff check.
- Use a pyproject.toml file in the root of this project to define the project, ruff configuration, and pixi configuration. We want two pixi environments, one for development and a default.

# Initial project requirements.

1. A side-scrolling video game based on pygame that we will eventually port to the web.
2. Automatic terrain generation that is unique during each run.
3. The game should look like a retro 1970's/1980's video game with fluorescent green line graphics if possible.
4. The lander will start with some random velocity and flight path angle at an altitude of 20 km above the moon, which we will model as a rectilinear gravity field (x and y motion only).
5. The default controls will use the A and D keys to rotate the vehicle left and right, and the space bar will fire thrusters at full throttle.
6. We will allow mapping of mouse or joystick axes to these controls