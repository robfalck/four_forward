"""Camera: world-to-screen transform with altitude-adaptive zoom."""

from __future__ import annotations

from .constants import (
    LANDER_SCREEN_Y_FRAC,
    SCREEN_H,
    SCREEN_W,
    ZOOM_ALT_FRAC,
    ZOOM_MAX,
    ZOOM_MIN,
)


class Camera:
    def __init__(self) -> None:
        self.x: float = 0.0    # world x at screen centre
        self.y: float = 0.0    # world y at screen centre
        self.zoom: float = ZOOM_MIN  # pixels per metre

    def track(self, lander_x: float, lander_y: float, altitude: float) -> None:
        """Re-centre the camera on the lander, adjusting zoom for altitude."""
        self.x = lander_x

        # Zoom: keep the altitude gap at ZOOM_ALT_FRAC of screen height
        target_alt_px = SCREEN_H * ZOOM_ALT_FRAC
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, target_alt_px / max(altitude, 1.0)))

        # Camera y: place the lander at LANDER_SCREEN_Y_FRAC from the top
        # world_to_screen: sy = H/2 - (wy - cam_y) * zoom = LANDER_SCREEN_Y_FRAC * H
        # => cam_y = lander_y - (H/2 - LANDER_SCREEN_Y_FRAC * H) / zoom
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
