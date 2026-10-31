"""Difficulty presets: landing-pad size and safe touchdown speed."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import PAD_WIDTH, SAFE_VERT_SPEED


@dataclass(frozen=True)
class Difficulty:
    name: str
    pad_width: float        # metres
    safe_vert_speed: float  # m/s max downward speed for a successful pad landing
    score_mult: float       # landing score multiplier (see scoring.py)


EASY = Difficulty("EASY", PAD_WIDTH * 2.0, 15.0, 1.0)
MEDIUM = Difficulty("MEDIUM", float(PAD_WIDTH), SAFE_VERT_SPEED, 1.5)
HARD = Difficulty("HARD", PAD_WIDTH * 0.75, SAFE_VERT_SPEED, 2.0)

DIFFICULTIES: tuple[Difficulty, ...] = (EASY, MEDIUM, HARD)
DEFAULT_DIFFICULTY = MEDIUM
