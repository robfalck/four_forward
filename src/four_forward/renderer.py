"""Retro phosphor-green vector renderer."""

from __future__ import annotations

import math
import random

import pygame

from .camera import Camera
from .constants import (
    COLOR_BG,
    COLOR_GREEN,
    COLOR_GREEN_DIM,
    COLOR_GREEN_MID,
    LANDER_ART_SCALE_M,
    LANDER_GROUND_OFFSET_M,
    MOON_GRAVITY,
    SAFE_VERT_SPEED,
    SCREEN_H,
    SCREEN_W,
    TITLE,
)
from .lander import Lander
from .terrain import Terrain

_N_STARS = 180           # background star count
_STAR_PARALLAX = 0.002   # how much stars shift per metre of camera x
_LANDER_MIN_PX = 12      # minimum pixel scale so lander stays readable at high altitude


def _ballistic_landing_x(lander: Lander, terrain: Terrain) -> float | None:
    """
    Predict landing X assuming ballistic coast (no future thrust).
    Uses terrain height at current lander x as a flat-ground approximation.
    Returns None if the lander is climbing and can never land (unlikely on the moon).
    """
    eff_alt = lander.y - terrain.height_at(lander.x) - LANDER_GROUND_OFFSET_M
    if eff_alt <= 0:
        return None
    disc = lander.vy ** 2 + 2.0 * MOON_GRAVITY * eff_alt
    if disc < 0:
        return None
    t = (lander.vy + math.sqrt(disc)) / MOON_GRAVITY
    if t <= 0 or t > 600.0:   # ignore predictions > 10 minutes out
        return None
    return lander.x + lander.vx * t


class Renderer:
    def __init__(self) -> None:
        # Font — monospace for that terminal HUD feel
        self.font = pygame.font.SysFont("Courier New", 14, bold=False)
        self.font_large = pygame.font.SysFont("Courier New", 28, bold=True)

        # Generate a fixed star field (screen-space base positions)
        rng = random.Random(42)
        self._stars = [
            (rng.randint(0, SCREEN_W), rng.randint(0, SCREEN_H))
            for _ in range(_N_STARS)
        ]

        # Pre-build scanline overlay surface for CRT effect
        self._scanlines = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for y in range(0, SCREEN_H, 3):
            pygame.draw.line(self._scanlines, (0, 0, 0, 55), (0, y), (SCREEN_W, y))

        self._flame_rng = random.Random()

        # Surface for terrain fade-in effect
        self._terrain_surf = pygame.Surface((SCREEN_W, SCREEN_H))
        self._terrain_surf.set_colorkey(COLOR_BG)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def draw(
        self,
        screen: pygame.Surface,
        terrain: Terrain,
        lander: Lander,
        camera: Camera,
        state: str,
        crash_reason: str = "",
    ) -> None:
        screen.fill(COLOR_BG)
        self._draw_stars(screen, camera)
        alt = lander.y - terrain.height_at(lander.x)
        if alt <= 1500.0:
            self._draw_terrain(screen, terrain, camera)
        elif alt < 2000.0:
            fade_alpha = int(255 * (2000.0 - alt) / 500.0)
            self._terrain_surf.fill(COLOR_BG)
            self._draw_terrain(self._terrain_surf, terrain, camera)
            self._terrain_surf.set_alpha(fade_alpha)
            screen.blit(self._terrain_surf, (0, 0))
        self._draw_lander(screen, lander, camera)
        self._draw_hud(screen, lander, terrain, state)
        self._draw_minimap(screen, terrain, lander, camera)
        if state == "setup":
            self._draw_setup_overlay(screen)
        elif state in ("landed", "crashed"):
            self._draw_overlay(screen, state, lander, crash_reason)
        screen.blit(self._scanlines, (0, 0))

    # ------------------------------------------------------------------
    # Stars
    # ------------------------------------------------------------------

    def _draw_stars(self, screen: pygame.Surface, camera: Camera) -> None:
        for bx, by in self._stars:
            sx = int((bx - camera.x * _STAR_PARALLAX) % SCREEN_W)
            screen.set_at((sx, by), COLOR_GREEN_DIM)

    # ------------------------------------------------------------------
    # Terrain
    # ------------------------------------------------------------------

    def _draw_terrain(self, screen: pygame.Surface, terrain: Terrain, camera: Camera) -> None:
        pts = terrain.points_in_range(camera.world_x_min, camera.world_x_max)
        if len(pts) < 2:
            return

        screen_pts = [camera.world_to_screen(wx, wy) for wx, wy in pts]

        # Draw the terrain surface line
        pygame.draw.lines(screen, COLOR_GREEN_MID, False, screen_pts, 2)

        # Draw landing pads brighter with tick marks
        for pad_start, pad_end in terrain.pads:
            wx0 = pad_start * terrain.step
            wx1 = pad_end * terrain.step
            if wx1 < camera.world_x_min or wx0 > camera.world_x_max:
                continue
            wy = terrain.heights[pad_start]
            sx0, sy0 = camera.world_to_screen(wx0, wy)
            sx1, _ = camera.world_to_screen(wx1, wy)
            pygame.draw.line(screen, COLOR_GREEN, (sx0, sy0), (sx1, sy0), 2)
            # Vertical tick at each end
            pygame.draw.line(screen, COLOR_GREEN, (sx0, sy0 - 6), (sx0, sy0 + 6), 1)
            pygame.draw.line(screen, COLOR_GREEN, (sx1, sy0 - 6), (sx1, sy0 + 6), 1)

    # ------------------------------------------------------------------
    # Lander
    # ------------------------------------------------------------------

    def _draw_lander(self, screen: pygame.Surface, lander: Lander, camera: Camera) -> None:
        if not lander.alive and not lander.landed:
            self._draw_crash(screen, lander, camera)
            return

        sx, sy = camera.world_to_screen(lander.x, lander.y)
        angle = lander.theta
        scale = max(float(_LANDER_MIN_PX), camera.zoom * LANDER_ART_SCALE_M)

        def rot(px: float, py: float) -> tuple[int, int]:
            """Rotate local lander coords and map to screen pixels."""
            rx = px * math.cos(angle) - py * math.sin(angle)
            ry = px * math.sin(angle) + py * math.cos(angle)
            return int(sx + rx * scale), int(sy - ry * scale)

        # --- Apollo LM line art ---

        # Descent stage (wide box with equipment-bay panel line)
        ds = [(-0.47, -0.31), (0.47, -0.31), (0.47, 0.07), (-0.47, 0.07)]
        pygame.draw.polygon(screen, COLOR_GREEN, [rot(x, y) for x, y in ds], 1)
        pygame.draw.line(screen, COLOR_GREEN_MID, rot(-0.47, -0.11), rot(0.47, -0.11), 1)

        # Ascent stage — octagonal (chamfered top corners)
        asc = [
            (-0.21, 0.07), (0.21, 0.07),
            (0.21, 0.36), (0.12, 0.46),
            (-0.12, 0.46), (-0.21, 0.36),
        ]
        pygame.draw.polygon(screen, COLOR_GREEN, [rot(x, y) for x, y in asc], 1)

        # Docking tunnel (small box on top of ascent stage)
        pygame.draw.line(screen, COLOR_GREEN, rot(-0.05, 0.46), rot(-0.05, 0.56), 1)
        pygame.draw.line(screen, COLOR_GREEN, rot(0.05, 0.46), rot(0.05, 0.56), 1)
        pygame.draw.line(screen, COLOR_GREEN, rot(-0.05, 0.56), rot(0.05, 0.56), 1)

        # Two triangular windows (most distinctive LM feature)
        pygame.draw.polygon(
            screen, COLOR_GREEN,
            [rot(-0.18, 0.12), rot(-0.04, 0.12), rot(-0.11, 0.26)], 1
        )
        pygame.draw.polygon(
            screen, COLOR_GREEN,
            [rot(0.04, 0.12), rot(0.18, 0.12), rot(0.11, 0.26)], 1
        )

        # RCS thruster pods (small rectangular protrusions on ascent stage sides)
        for side in (-1, 1):
            pygame.draw.line(screen, COLOR_GREEN, rot(side * 0.21, 0.22), rot(side * 0.30, 0.22), 1)
            pygame.draw.line(screen, COLOR_GREEN, rot(side * 0.21, 0.29), rot(side * 0.30, 0.29), 1)
            pygame.draw.line(screen, COLOR_GREEN, rot(side * 0.30, 0.22), rot(side * 0.30, 0.29), 1)

        # Antenna (from ascent stage top)
        pygame.draw.line(screen, COLOR_GREEN, rot(0.10, 0.46), rot(0.28, 0.67), 1)
        pygame.draw.circle(screen, COLOR_GREEN, rot(0.28, 0.67), 2, 0)

        # Engine nozzle bell (flared, below descent stage)
        pygame.draw.line(screen, COLOR_GREEN, rot(-0.11, -0.31), rot(-0.18, -0.60), 1)
        pygame.draw.line(screen, COLOR_GREEN, rot(0.11, -0.31), rot(0.18, -0.60), 1)
        pygame.draw.line(screen, COLOR_GREEN, rot(-0.18, -0.60), rot(0.18, -0.60), 1)

        # Landing legs — primary strut + brace + diagonal cross-member + foot pad
        for side in (-1, 1):
            attach_hi = rot(side * 0.47, -0.08)
            attach_lo = rot(side * 0.47, -0.26)
            tip = rot(side * 0.92, -0.80)
            mid_primary = rot(side * 0.695, -0.44)   # midpoint of primary strut
            pygame.draw.line(screen, COLOR_GREEN, attach_hi, tip, 1)       # primary strut
            pygame.draw.line(screen, COLOR_GREEN, attach_lo, tip, 1)       # brace strut
            pygame.draw.line(screen, COLOR_GREEN, attach_lo, mid_primary, 1)  # cross-member
            pad_l = rot(side * 0.82, -0.80)
            pad_r = rot(side * 1.02, -0.80)
            pygame.draw.line(screen, COLOR_GREEN, pad_l, pad_r, 2)         # foot pad

        # Thrust flame from nozzle exit
        if lander.thrusting:
            fl = self._flame_rng.uniform(0.5, 1.1)
            tip = rot(self._flame_rng.uniform(-0.07, 0.07), -0.60 - fl * 0.55)
            fleft = rot(-0.14, -0.60)
            fright = rot(0.14, -0.60)
            pygame.draw.polygon(screen, COLOR_GREEN_MID, [fleft, fright, tip], 0)

    def _draw_crash(self, screen: pygame.Surface, lander: Lander, camera: Camera) -> None:
        # Explosion centred at foot-pad level, not lander body centre
        impact_y = lander.y - LANDER_GROUND_OFFSET_M
        sx, sy = camera.world_to_screen(lander.x, impact_y)
        scale = max(float(_LANDER_MIN_PX), camera.zoom * LANDER_ART_SCALE_M)
        for i in range(8):
            a = i * math.pi / 4.0
            ex = int(sx + math.cos(a) * scale)
            ey = int(sy - math.sin(a) * scale)
            pygame.draw.line(screen, COLOR_GREEN_MID, (sx, sy), (ex, ey), 1)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _draw_hud(
        self, screen: pygame.Surface, lander: Lander, terrain: Terrain, state: str
    ) -> None:
        alt = lander.y - terrain.height_at(lander.x)
        lines = [
            f"ALT   {alt:>8.0f} m",
            f"VERT  {lander.vy:>+8.1f} m/s",
            f"HORZ  {lander.vx:>+8.1f} m/s",
            f"ANGLE {lander.theta_deg:>+8.1f} deg",
            f"FUEL  {lander.fuel_fraction * 100:>7.1f} %",
        ]
        for i, line in enumerate(lines):
            surf = self.font.render(line, True, COLOR_GREEN)
            screen.blit(surf, (12, 12 + i * 18))

        # Fuel bar
        bar_x, bar_y = 12, 12 + len(lines) * 18 + 4
        bar_w = 120
        bar_h = 6
        pygame.draw.rect(screen, COLOR_GREEN_DIM, (bar_x, bar_y, bar_w, bar_h))
        filled = int(bar_w * lander.fuel_fraction)
        pygame.draw.rect(screen, COLOR_GREEN, (bar_x, bar_y, filled, bar_h))

        # Approach status — only meaningful while flying
        if state == "playing":
            status_y = bar_y + bar_h + 10

            # Vertical speed vs landing threshold
            vspd = lander.vert_speed
            spd_ok = vspd <= SAFE_VERT_SPEED
            spd_label = "SAFE" if spd_ok else "FAST"
            spd_str = f"SPEED {vspd:>5.1f}  {spd_label}"
            spd_col = COLOR_GREEN if spd_ok else COLOR_GREEN_MID
            screen.blit(self.font.render(spd_str, True, spd_col), (12, status_y))

            # Ballistic pad prediction
            pred_x = _ballistic_landing_x(lander, terrain)
            if pred_x is not None:
                on_pad = terrain.is_on_pad(pred_x)
                pad_label = "ON COURSE " if on_pad else "OFF COURSE"
                pad_str = f"PAD   {pad_label}"
                pad_col = COLOR_GREEN if on_pad else COLOR_GREEN_MID
                screen.blit(self.font.render(pad_str, True, pad_col), (12, status_y + 18))

        # Title above minimap
        title_surf = self.font.render(TITLE, True, COLOR_GREEN_DIM)
        mm_x = SCREEN_W - 260 - 12
        screen.blit(title_surf, (mm_x + (260 - title_surf.get_width()) // 2, 14))

        # Controls reminder at bottom
        if state == "setup":
            hint = "SPACE LAUNCH   N NEW TERRAIN   ESC QUIT"
        else:
            hint = "A/D ROTATE   SPACE THRUST   R RESTART"
        hint_surf = self.font.render(hint, True, COLOR_GREEN_DIM)
        screen.blit(hint_surf, ((SCREEN_W - hint_surf.get_width()) // 2, SCREEN_H - 22))

    # ------------------------------------------------------------------
    # Minimap
    # ------------------------------------------------------------------

    def _draw_minimap(
        self, screen: pygame.Surface, terrain: Terrain, lander: Lander, camera: Camera
    ) -> None:
        mm_w, mm_h = 260, 80
        mm_x = SCREEN_W - mm_w - 12
        mm_y = 32  # just below title text

        # Background and border
        pygame.draw.rect(screen, (0, 8, 0), (mm_x, mm_y, mm_w, mm_h))
        pygame.draw.rect(screen, COLOR_GREEN_DIM, (mm_x, mm_y, mm_w, mm_h), 1)

        max_h = max(terrain.heights) or 1.0

        def wx_to_mm(wx: float) -> int:
            return mm_x + int(wx / terrain.width * mm_w)

        def wy_to_mm(wy: float) -> int:
            return mm_y + mm_h - 1 - int(wy / max_h * (mm_h - 4))

        # Terrain profile — subsample to one point per pixel column
        step = max(1, len(terrain.heights) // mm_w)
        pts = [
            (wx_to_mm(i * terrain.step), wy_to_mm(terrain.heights[i]))
            for i in range(0, len(terrain.heights), step)
        ]
        if len(pts) >= 2:
            pygame.draw.lines(screen, COLOR_GREEN_DIM, False, pts, 1)

        # Landing pads (brighter)
        for pad_start, pad_end in terrain.pads:
            px0 = wx_to_mm(pad_start * terrain.step)
            px1 = wx_to_mm(pad_end * terrain.step)
            py = wy_to_mm(terrain.heights[pad_start])
            pygame.draw.line(screen, COLOR_GREEN, (px0, py), (px1, py), 2)

        # Ballistic trajectory landing prediction marker (dashed vertical line)
        pred_x = _ballistic_landing_x(lander, terrain)
        if pred_x is not None:
            pred_mm = max(mm_x, min(mm_x + mm_w - 1, wx_to_mm(pred_x)))
            for dash_y in range(mm_y + 1, mm_y + mm_h - 1, 5):
                end_y = min(dash_y + 3, mm_y + mm_h - 1)
                pygame.draw.line(screen, COLOR_GREEN_MID, (pred_mm, dash_y), (pred_mm, end_y), 1)

        # Camera viewport rectangle (field of view indicator)
        vx0 = max(mm_x, min(mm_x + mm_w, wx_to_mm(camera.world_x_min)))
        vx1 = max(mm_x, min(mm_x + mm_w, wx_to_mm(camera.world_x_max)))
        if vx1 > vx0:
            pygame.draw.rect(screen, COLOR_GREEN_MID, (vx0, mm_y, vx1 - vx0, mm_h), 1)

        # Lander dot — x mapped to minimap, y clamped inside minimap
        lx = max(mm_x, min(mm_x + mm_w - 1, wx_to_mm(lander.x)))
        ly = max(mm_y + 2, min(mm_y + mm_h - 3, wy_to_mm(lander.y)))
        pygame.draw.circle(screen, COLOR_GREEN, (lx, ly), 2)

    # ------------------------------------------------------------------
    # Setup overlay
    # ------------------------------------------------------------------

    def _draw_setup_overlay(self, screen: pygame.Surface) -> None:
        msg_surf = self.font_large.render("READY FOR LAUNCH", True, COLOR_GREEN)
        sub_surf = self.font.render("SPACE to launch   N to new terrain", True, COLOR_GREEN_MID)
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        screen.blit(msg_surf, (cx - msg_surf.get_width() // 2, cy - 28))
        screen.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy + 16))

    # ------------------------------------------------------------------
    # Game-over overlay
    # ------------------------------------------------------------------

    def _draw_overlay(
        self, screen: pygame.Surface, state: str, lander: Lander, crash_reason: str = ""
    ) -> None:
        if state == "landed":
            msg = "TOUCHDOWN"
            lines = [f"FUEL REMAINING  {lander.fuel_fraction * 100:.1f}%", "PRESS R TO CONTINUE"]
            color = COLOR_GREEN
        else:
            msg = "SPACECRAFT LOST"
            lines = [crash_reason, "PRESS R TO RETRY"] if crash_reason else ["PRESS R TO RETRY"]
            color = COLOR_GREEN_MID

        msg_surf = self.font_large.render(msg, True, color)
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        screen.blit(msg_surf, (cx - msg_surf.get_width() // 2, cy - 36))
        for i, line in enumerate(lines):
            sub_surf = self.font.render(line, True, COLOR_GREEN_MID)
            screen.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy + 10 + i * 20))
