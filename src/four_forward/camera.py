"""Camera: world-to-screen transform with altitude-adaptive zoom."""

from __future__ import annotations

from .constants import (
    LANDER_SCREEN_Y_FRAC,
    SCREEN_H,
    SCREEN_W,
    ZOOM_FIXED,
)


class Camera:
    def __init__(self) -> None:
        self.x: float = 0.0    # world x at screen centre
        self.y: float = 0.0    # world y at screen centre
        self.zoom: float = ZOOM_FIXED  # pixels per metre (fixed)

    def track(self, lander_x: float, lander_y: float, altitude: float) -> None:
        """Re-centre the camera on the lander (fixed zoom)."""
        self.x = lander_x

        # Camera y: place the lander at LANDER_SCREEN_Y_FRAC from the top
        self.y = lander_y - (SCREEN_H / 2.0 - LANDER_SCREEN_Y_FRAC * SCREEN_H) / self.zoom

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        sx = (wx - self.x) * self.zoom + SCREEN_W / 2.0
        sy = SCREEN_H / 2.0 - (wy - self.y) * self.zoom
        return int(sx), int(sy)

    def screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        wx = (sx - SCREEN_W / 2.0) / self.zoom + self.x
        wy = self.y - (sy - SCREEN_H / 2.0) / self.zoom
        return wx, wy

    @property
    def world_x_min(self) -> float:
        wx, _ = self.screen_to_world(0, 0)
        return wx

    @property
    def world_x_max(self) -> float:
        wx, _ = self.screen_to_world(SCREEN_W, 0)
        return wx

    @property
    def world_y_min(self) -> float:
        """World y at the bottom edge of the screen."""
        _, wy = self.screen_to_world(0, SCREEN_H)
        return wy

    @property
    def world_y_max(self) -> float:
        """World y at the top edge of the screen."""
        _, wy = self.screen_to_world(0, 0)
        return wy
