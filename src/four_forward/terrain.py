"""Procedural moon terrain generation via midpoint displacement."""

import random

from .constants import N_PADS, PAD_WIDTH, TERRAIN_AMPLITUDE, TERRAIN_STEP, TERRAIN_WIDTH


class Terrain:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.step = TERRAIN_STEP
        self.width = TERRAIN_WIDTH
        n = TERRAIN_WIDTH // TERRAIN_STEP + 1
        self.heights: list[float] = [0.0] * n
        self._generate()
        # Shift so minimum height == 0
        min_h = min(self.heights)
        self.heights = [h - min_h for h in self.heights]
        # Landing pads: list of (start_idx, end_idx) index pairs
        self.pads: list[tuple[int, int]] = []
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
        pad_pts = PAD_WIDTH // TERRAIN_STEP
        spacing = n // (N_PADS + 1)
        for i in range(N_PADS):
            center = spacing * (i + 1)
            start = max(0, center - pad_pts // 2)
            end = min(n - 1, start + pad_pts)
            avg_h = sum(self.heights[start : end + 1]) / (end - start + 1)
            for j in range(start, end + 1):
                self.heights[j] = avg_h
            self.pads.append((start, end))

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
        idx = int(x / self.step)
        return any(start <= idx <= end for start, end in self.pads)

    def points_in_range(self, x_min: float, x_max: float) -> list[tuple[float, float]]:
        """World-space (x, y) points for the terrain segment visible in [x_min, x_max]."""
        idx_lo = max(0, int(x_min / self.step) - 1)
        idx_hi = min(len(self.heights) - 1, int(x_max / self.step) + 2)
        return [(i * self.step, self.heights[i]) for i in range(idx_lo, idx_hi + 1)]
