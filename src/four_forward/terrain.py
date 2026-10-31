"""Procedural moon terrain generation via midpoint displacement."""

import math
import random

from .constants import N_PADS, PAD_WIDTH, TERRAIN_AMPLITUDE, TERRAIN_STEP, TERRAIN_WIDTH


class Terrain:
    def __init__(self, seed: int | None = None, pad_width: float = PAD_WIDTH) -> None:
        self._rng = random.Random(seed)
        self.step = TERRAIN_STEP
        self.width = TERRAIN_WIDTH
        n = TERRAIN_WIDTH // TERRAIN_STEP + 1
        self.heights: list[float] = [0.0] * n
        self._generate()
        # Shift so minimum height == 0
        min_h = min(self.heights)
        self.heights = [h - min_h for h in self.heights]
        # Landing pads: list of (x_start, x_end) world-space extents in metres
        self.pad_width = float(pad_width)
        self.pads: list[tuple[float, float]] = []
        self._add_pads()

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _generate(self) -> None:
        n = len(self.heights)
        self.heights[0] = self._rng.uniform(-200, 200)
        self.heights[-1] = self._rng.uniform(-200, 200)
        self._displace(0, n - 1, float(TERRAIN_AMPLITUDE))

    def _displace(self, lo: int, hi: int, scale: float) -> None:
        if hi - lo <= 1:
            return
        mid = (lo + hi) // 2
        self.heights[mid] = (self.heights[lo] + self.heights[hi]) / 2 + self._rng.uniform(
            -scale, scale
        )
        self._displace(lo, mid, scale * 0.72)
        self._displace(mid, hi, scale * 0.72)

    def _add_pads(self) -> None:
        n = len(self.heights)
        spacing = n // (N_PADS + 1)
        for i in range(N_PADS):
            x_mid = spacing * (i + 1) * self.step
            x0 = max(0.0, x_mid - self.pad_width / 2.0)
            x1 = min(float(self.width), x0 + self.pad_width)
            # Flatten every sample spanning the pad so it is level edge to edge
            start = int(x0 // self.step)
            end = min(n - 1, math.ceil(x1 / self.step))
            avg_h = sum(self.heights[start : end + 1]) / (end - start + 1)
            for j in range(start, end + 1):
                self.heights[j] = avg_h
            self.pads.append((x0, x1))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def mean_height(self) -> float:
        return sum(self.heights) / len(self.heights)

    def height_at(self, x: float) -> float:
        """Linearly interpolated terrain height (meters) at world x."""
        idx = x / self.step
        lo = max(0, min(int(idx), len(self.heights) - 2))
        frac = idx - lo
        return self.heights[lo] * (1.0 - frac) + self.heights[lo + 1] * frac

    def is_on_pad(self, x: float) -> bool:
        """True if world x falls within a designated landing pad."""
        return self.pad_number(x) is not None

    def pad_number(self, x: float) -> int | None:
        """1-based index (left to right) of the pad containing world x, or None."""
        for i, (x0, x1) in enumerate(self.pads, start=1):
            if x0 <= x <= x1:
                return i
        return None

    def points_in_range(self, x_min: float, x_max: float) -> list[tuple[float, float]]:
        """World-space (x, y) points for the terrain segment visible in [x_min, x_max]."""
        idx_lo = max(0, int(x_min / self.step) - 1)
        idx_hi = min(len(self.heights) - 1, int(x_max / self.step) + 2)
        return [(i * self.step, self.heights[i]) for i in range(idx_lo, idx_hi + 1)]
