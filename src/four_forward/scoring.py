"""Landing score: fuel remaining × difficulty × pad × speed multipliers.

The worldwide leaderboard recomputes the same formula in SQL
(supabase/leaderboard.sql); keep the two in sync.
"""

from __future__ import annotations

from dataclasses import dataclass

from .difficulty import Difficulty

PAD_MULT_STEP = 0.25     # pad 1 ×1.00, pad 2 ×1.25, pad 3 ×1.50, pad 4 ×1.75
FAST_TIME_S = 120.0      # at or under this flight time → SPEED_MULT_MAX
SLOW_TIME_S = 360.0      # at or over this flight time  → SPEED_MULT_MIN
SPEED_MULT_MAX = 1.5
SPEED_MULT_MIN = 0.75


def pad_multiplier(pad: int) -> float:
    """pad is 1-based, counted left to right."""
    return 1.0 + PAD_MULT_STEP * (pad - 1)


def speed_multiplier(flight_time: float) -> float:
    frac = (flight_time - FAST_TIME_S) / (SLOW_TIME_S - FAST_TIME_S)
    frac = max(0.0, min(1.0, frac))
    return SPEED_MULT_MAX - (SPEED_MULT_MAX - SPEED_MULT_MIN) * frac


@dataclass(frozen=True)
class ScoreBreakdown:
    fuel: float          # kg remaining at touchdown
    difficulty: Difficulty
    pad: int             # 1-based
    flight_time: float   # seconds from launch to touchdown

    @property
    def difficulty_mult(self) -> float:
        return self.difficulty.score_mult

    @property
    def pad_mult(self) -> float:
        return pad_multiplier(self.pad)

    @property
    def speed_mult(self) -> float:
        return speed_multiplier(self.flight_time)

    @property
    def total(self) -> int:
        return round(self.fuel * self.difficulty_mult * self.pad_mult * self.speed_mult)
