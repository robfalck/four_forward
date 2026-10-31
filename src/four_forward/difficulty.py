"""Difficulty presets: landing-pad size and safe touchdown speed and tilt."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import PAD_WIDTH, SAFE_ANGLE, SAFE_VERT_SPEED


@dataclass(frozen=True)
class Difficulty:
    name: str
    pad_width: float        # metres
    safe_vert_speed: float  # m/s max downward speed for a successful pad landing
    safe_tilt_deg: float    # max tilt from upright for a successful pad landing
    score_mult: float       # landing score multiplier (see scoring.py)


EASY = Difficulty("EASY", PAD_WIDTH * 2.0, 15.0, SAFE_ANGLE * 1.25, 1.0)
MEDIUM = Difficulty("MEDIUM", float(PAD_WIDTH), SAFE_VERT_SPEED, SAFE_ANGLE, 1.5)
HARD = Difficulty("HARD", PAD_WIDTH * 0.75, SAFE_VERT_SPEED, SAFE_ANGLE * 0.75, 2.0)

DIFFICULTIES: tuple[Difficulty, ...] = (EASY, MEDIUM, HARD)
DEFAULT_DIFFICULTY = MEDIUM
