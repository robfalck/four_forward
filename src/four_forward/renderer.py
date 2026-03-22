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
from .leaderboard import Leaderboard
from .terrain import Terrain

_N_STARS = 180           # background star count
_STAR_PARALLAX = 0.6     # px of star movement per metre of camera travel
_LANDER_MIN_PX = 28      # minimum pixel scale — keeps lander large and readable at altitude


def _ballistic_trajectory(
    lander: Lander, terrain: Terrain, n_pts: int = 40
) -> list[tuple[float, float]]:
    """
    Sample the ballistic (no-thrust) trajectory from lander to foot-pad ground contact.
    Returns list of world-space (x, y) points, empty if not applicable.
    Uses flat-ground approximation (terrain height at current lander x).
    """
    eff_alt = lander.y - terrain.height_at(lander.x) - LANDER_GROUND_OFFSET_M
    if eff_alt <= 0:
        return []
    disc = lander.vy ** 2 + 2.0 * MOON_GRAVITY * eff_alt
    if disc < 0:
        return []
    t_land = (lander.vy + math.sqrt(disc)) / MOON_GRAVITY
    if t_land <= 0 or t_land > 600.0:
        return []
    return [
        (
            lander.x + lander.vx * t_land * i / n_pts,
            lander.y
            + lander.vy * t_land * i / n_pts
            - 0.5 * MOON_GRAVITY * (t_land * i / n_pts) ** 2,
        )
        for i in range(n_pts + 1)
    ]


def _ballistic_landing_x(lander: Lander, terrain: Terrain) -> float | None:
    """Predict ballistic landing X. Returns None if not applicable."""
    pts = _ballistic_trajectory(lander, terrain, n_pts=1)
    return pts[-1][0] if pts else None


class Renderer:
    def __init__(self) -> None:
        # Font — monospace for that terminal HUD feel
        self.font = pygame.font.SysFont("Courier New", 14, bold=False)
        self.font_large = pygame.font.SysFont("Courier New", 28, bold=True)

        # Generate a fixed star field (screen-space positions + radius)
        rng = random.Random(42)
        self._stars = [
            (rng.randint(0, SCREEN_W), rng.randint(0, SCREEN_H),
             rng.choices([1, 2], weights=[3, 1])[0])
            for _ in range(_N_STARS)
        ]

        # Pre-build scanline overlay surface for CRT effect
        self._scanlines = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for y in range(0, SCREEN_H, 3):
            pygame.draw.line(self._scanlines, (0, 0, 0, 55), (0, y), (SCREEN_W, y))

        self._flame_rng = random.Random()

        # Off-screen surface used to fade terrain in below 2000 m
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
        leaderboard: Leaderboard | None = None,
        player_name: str = "",
    ) -> None:
        if state == "splash":
            screen.fill(COLOR_BG)
            self._draw_stars(screen, camera)
            self._draw_splash(screen)
            screen.blit(self._scanlines, (0, 0))
            return

        screen.fill(COLOR_BG)
        self._draw_stars(screen, camera)
        alt = lander.y - terrain.height_at(lander.x)
        if alt <= 1500.0:
            self._draw_terrain(screen, terrain, camera)
        elif alt < 2000.0:
            self._terrain_surf.fill(COLOR_BG)
            self._draw_terrain(self._terrain_surf, terrain, camera)
            self._terrain_surf.set_alpha(int(255 * (2000.0 - alt) / 500.0))
            screen.blit(self._terrain_surf, (0, 0))
        self._draw_lander(screen, lander, camera)
        self._draw_hud(screen, lander, terrain, state)
        self._draw_minimap(screen, terrain, lander, camera)
        if state == "setup":
            self._draw_setup_overlay(screen)
        elif state == "leaderboard":
            if leaderboard is not None:
                self._draw_leaderboard_screen(screen, leaderboard)
        elif state == "name_entry":
            self._draw_name_entry(screen, lander, player_name)
        elif state == "landed":
            self._draw_overlay(screen, state, lander, crash_reason)
            if leaderboard is not None:
                self._draw_leaderboard(screen, leaderboard, lander.m_fuel)
        elif state == "crashed":
            self._draw_overlay(screen, state, lander, crash_reason)
        screen.blit(self._scanlines, (0, 0))

    # ------------------------------------------------------------------
    # Stars
    # ------------------------------------------------------------------

    def _draw_stars(self, screen: pygame.Surface, camera: Camera) -> None:
        offset = camera.x * _STAR_PARALLAX
        for bsx, sy, r in self._stars:
            sx = int((bsx - offset) % SCREEN_W)
            pygame.draw.circle(screen, COLOR_GREEN_DIM, (sx, sy), r)

    # ------------------------------------------------------------------
    # Terrain
    # ------------------------------------------------------------------

    def _draw_terrain(self, screen: pygame.Surface, terrain: Terrain, camera: Camera) -> None:
        pts = terrain.points_in_range(camera.world_x_min, camera.world_x_max)
        if len(pts) < 2:
            return

        screen_pts = [camera.world_to_screen(wx, wy) for wx, wy in pts]
        pygame.draw.lines(screen, COLOR_GREEN_MID, False, screen_pts, 2)

        for pad_start, pad_end in terrain.pads:
            wx0 = pad_start * terrain.step
            wx1 = pad_end * terrain.step
            if wx1 < camera.world_x_min or wx0 > camera.world_x_max:
                continue
            wy = terrain.heights[pad_start]
            sx0, sy0 = camera.world_to_screen(wx0, wy)
            sx1, _ = camera.world_to_screen(wx1, wy)
            pygame.draw.line(screen, COLOR_GREEN, (sx0, sy0), (sx1, sy0), 2)
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
            rx = px * math.cos(angle) - py * math.sin(angle)
            ry = px * math.sin(angle) + py * math.cos(angle)
            return int(sx + rx * scale), int(sy - ry * scale)

        # Body triangle -- nose up, base at bottom
        nose = rot(0.0, 1.0)
        left = rot(-0.5, -0.5)
        right = rot(0.5, -0.5)
        pygame.draw.polygon(screen, COLOR_GREEN, [nose, left, right], 1)

        # Landing legs -- struts from lower triangle corners to foot pads
        pygame.draw.line(screen, COLOR_GREEN, left, rot(-0.8, -0.80), 1)
        pygame.draw.line(screen, COLOR_GREEN, right, rot(0.8, -0.80), 1)

        # Thrust flame -- randomised polygon below the base
        if lander.thrusting:
            fl = self._flame_rng.uniform(0.6, 1.2)
            ftip = rot(self._flame_rng.uniform(-0.15, 0.15), -0.5 - fl)
            fleft = rot(-0.15, -0.5)
            fright = rot(0.15, -0.5)
            pygame.draw.polygon(screen, COLOR_GREEN_MID, [fleft, fright, ftip], 0)

    def _draw_crash(self, screen: pygame.Surface, lander: Lander, camera: Camera) -> None:
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
        bar_w, bar_h = 120, 6
        pygame.draw.rect(screen, COLOR_GREEN_DIM, (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * lander.fuel_fraction)
        pygame.draw.rect(screen, COLOR_GREEN, (bar_x, bar_y, fill_w, bar_h))

        # Approach status — only shown while flying
        if state == "playing":
            sy0 = bar_y + bar_h + 10
            vspd = lander.vert_speed
            spd_ok = vspd <= SAFE_VERT_SPEED
            spd_str = f"SPEED {vspd:>5.1f}  {'SAFE' if spd_ok else 'FAST'}"
            screen.blit(
                self.font.render(spd_str, True, COLOR_GREEN if spd_ok else COLOR_GREEN_MID),
                (12, sy0),
            )
            pred_x = _ballistic_landing_x(lander, terrain)
            if pred_x is not None:
                on_pad = terrain.is_on_pad(pred_x)
                pad_str = f"PAD   {'ON COURSE ' if on_pad else 'OFF COURSE'}"
                screen.blit(
                    self.font.render(pad_str, True, COLOR_GREEN if on_pad else COLOR_GREEN_MID),
                    (12, sy0 + 18),
                )

        # Title centred above minimap
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
        mm_y = 32

        pygame.draw.rect(screen, (0, 8, 0), (mm_x, mm_y, mm_w, mm_h))
        pygame.draw.rect(screen, COLOR_GREEN_DIM, (mm_x, mm_y, mm_w, mm_h), 1)

        max_h = max(terrain.heights) or 1.0
        # y range must encompass both terrain top and lander altitude for trajectory
        y_top = max(max_h * 1.1, lander.y * 1.05)

        def wx_to_mm(wx: float) -> int:
            return mm_x + int(wx / terrain.width * mm_w)

        def wy_to_mm(wy: float) -> int:
            return mm_y + mm_h - 1 - int(wy / y_top * (mm_h - 2))

        # Clip all minimap rendering to the rectangle so nothing bleeds out
        screen.set_clip(pygame.Rect(mm_x, mm_y, mm_w, mm_h))

        # Terrain profile
        step = max(1, len(terrain.heights) // mm_w)
        t_pts = [
            (wx_to_mm(i * terrain.step), wy_to_mm(terrain.heights[i]))
            for i in range(0, len(terrain.heights), step)
        ]
        if len(t_pts) >= 2:
            pygame.draw.lines(screen, COLOR_GREEN_DIM, False, t_pts, 1)

        # Landing pads (brighter)
        for pad_start, pad_end in terrain.pads:
            px0 = wx_to_mm(pad_start * terrain.step)
            px1 = wx_to_mm(pad_end * terrain.step)
            py = wy_to_mm(terrain.heights[pad_start])
            pygame.draw.line(screen, COLOR_GREEN, (px0, py), (px1, py), 2)

        # Ballistic trajectory — parabolic arc from lander to ground
        traj = _ballistic_trajectory(lander, terrain)
        if len(traj) >= 2:
            arc_pts = [(wx_to_mm(x), wy_to_mm(y)) for x, y in traj]
            pygame.draw.lines(screen, COLOR_GREEN_MID, False, arc_pts, 1)

        # Camera viewport rectangle
        vx0 = wx_to_mm(camera.world_x_min)
        vx1 = wx_to_mm(camera.world_x_max)
        pygame.draw.rect(screen, COLOR_GREEN_MID, (vx0, mm_y, vx1 - vx0, mm_h), 1)

        # Lander dot at true 2-D position
        pygame.draw.circle(screen, COLOR_GREEN, (wx_to_mm(lander.x), wy_to_mm(lander.y)), 2)

        screen.set_clip(None)

    # ------------------------------------------------------------------
    # Setup overlay
    # ------------------------------------------------------------------

    def _draw_setup_overlay(self, screen: pygame.Surface) -> None:
        msg_surf = self.font_large.render("READY FOR LAUNCH", True, COLOR_GREEN)
        sub_surf = self.font.render("SPACE to launch   N to new terrain", True, COLOR_GREEN_MID)
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        screen.blit(msg_surf, (cx - msg_surf.get_width() // 2, cy - 28))
        screen.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy + 16))

        # Leaderboard button — bottom left
        btn = self.font.render("[ L ]  LEADERBOARD", True, COLOR_GREEN_MID)
        screen.blit(btn, (16, SCREEN_H - btn.get_height() - 14))

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
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        screen.blit(msg_surf, (cx - msg_surf.get_width() // 2, cy - 36))
        for i, line in enumerate(lines):
            sub_surf = self.font.render(line, True, COLOR_GREEN_MID)
            screen.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy + 10 + i * 20))

    def _draw_name_entry(
        self, screen: pygame.Surface, lander: Lander, player_name: str
    ) -> None:
        cx, cy = SCREEN_W // 2, SCREEN_H // 2 - 60

        title = self.font_large.render("NEW HIGH SCORE!", True, COLOR_GREEN)
        screen.blit(title, (cx - title.get_width() // 2, cy))

        score_txt = f"FUEL REMAINING  {lander.m_fuel:.0f} kg"
        score_surf = self.font.render(score_txt, True, COLOR_GREEN_MID)
        screen.blit(score_surf, (cx - score_surf.get_width() // 2, cy + 44))

        prompt = self.font.render("ENTER YOUR NAME:", True, COLOR_GREEN_MID)
        screen.blit(prompt, (cx - prompt.get_width() // 2, cy + 72))

        # Name box
        box_w, box_h = 260, 28
        box_x, box_y = cx - box_w // 2, cy + 96
        pygame.draw.rect(screen, COLOR_GREEN_DIM, (box_x, box_y, box_w, box_h))
        pygame.draw.rect(screen, COLOR_GREEN, (box_x, box_y, box_w, box_h), 1)
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        name_surf = self.font.render(player_name + cursor, True, COLOR_GREEN)
        screen.blit(name_surf, (box_x + 8, box_y + 6))

        hint = self.font.render("ENTER to confirm   ESC to skip", True, COLOR_GREEN_DIM)
        screen.blit(hint, (cx - hint.get_width() // 2, cy + 136))

    def _draw_leaderboard(
        self, screen: pygame.Surface, lb: Leaderboard, current_score: float
    ) -> None:
        row_h = 18
        n_rows = len(lb.entries) + 2  # title + entries + padding
        lb_h = n_rows * row_h
        lb_x = SCREEN_W - 230
        lb_y = SCREEN_H - lb_h - 12

        title_surf = self.font.render("-- LEADERBOARD --", True, COLOR_GREEN)
        screen.blit(title_surf, (lb_x, lb_y))
        lb_y += row_h + 4

        for rank, entry in enumerate(lb.entries, start=1):
            is_current = abs(entry["score"] - current_score) < 0.5
            color = COLOR_GREEN if is_current else COLOR_GREEN_MID
            line = f"{rank:2}.  {entry['name']:<16}  {entry['score']:>5.0f} kg"
            surf = self.font.render(line, True, color)
            screen.blit(surf, (lb_x, lb_y))
            lb_y += row_h

    def _draw_leaderboard_screen(
        self, screen: pygame.Surface, lb: Leaderboard
    ) -> None:
        """Full-screen leaderboard view shown from the setup state."""
        cx = SCREEN_W // 2
        title = self.font_large.render("LEADERBOARD", True, COLOR_GREEN)
        screen.blit(title, (cx - title.get_width() // 2, 80))

        row_h = 22
        start_y = 140
        if not lb.entries:
            empty = self.font.render("NO SCORES YET", True, COLOR_GREEN_MID)
            screen.blit(empty, (cx - empty.get_width() // 2, start_y))
        else:
            for rank, entry in enumerate(lb.entries, start=1):
                line = f"{rank:2}.  {entry['name']:<16}  {entry['score']:>5.0f} kg fuel"
                surf = self.font.render(line, True, COLOR_GREEN_MID)
                screen.blit(surf, (cx - surf.get_width() // 2, start_y + (rank - 1) * row_h))

        hint = self.font.render("PRESS ANY KEY TO GO BACK", True, COLOR_GREEN_DIM)
        screen.blit(hint, (cx - hint.get_width() // 2, SCREEN_H - 40))

    # ------------------------------------------------------------------
    # Splash screen
    # ------------------------------------------------------------------

    def _draw_splash(self, screen: pygame.Surface) -> None:
        cx, cy = SCREEN_W // 2, SCREEN_H // 2

        # Title — two lines, large
        title1 = self.font_large.render("FOUR", True, COLOR_GREEN)
        title2 = self.font_large.render("FORWARD", True, COLOR_GREEN)
        screen.blit(title1, (cx - title1.get_width() // 2, cy - 80))
        screen.blit(title2, (cx - title2.get_width() // 2, cy - 44))

        # Decorative horizontal rules
        pygame.draw.line(screen, COLOR_GREEN_MID, (cx - 160, cy - 90), (cx - 10, cy - 90), 1)
        pygame.draw.line(screen, COLOR_GREEN_MID, (cx + 10, cy - 90), (cx + 160, cy - 90), 1)
        pygame.draw.line(screen, COLOR_GREEN_MID, (cx - 160, cy - 4), (cx + 160, cy - 4), 1)

        # Subtitle
        sub = self.font.render("LUNAR LANDER", True, COLOR_GREEN_MID)
        screen.blit(sub, (cx - sub.get_width() // 2, cy + 12))

        # Blinking prompt
        if (pygame.time.get_ticks() // 600) % 2 == 0:
            prompt = self.font.render("PRESS ANY KEY TO START", True, COLOR_GREEN_DIM)
            screen.blit(prompt, (cx - prompt.get_width() // 2, cy + 60))
