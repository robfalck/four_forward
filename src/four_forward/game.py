"""Main game loop."""

from __future__ import annotations

import asyncio
import time

import pygame

from .camera import Camera
from .constants import (
    FPS,
    INITIAL_ALTITUDE,
    LANDER_GROUND_OFFSET_M,
    SAFE_VERT_SPEED,
    SCREEN_H,
    SCREEN_W,
    TERRAIN_STEP,
    TERRAIN_WIDTH,
    TITLE,
)
from .controls import InputHandler
from .lander import Lander
from .leaderboard import Leaderboard
from .renderer import Renderer
from .terrain import Terrain

_MAX_NAME_LEN = 16


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self._input = InputHandler()
        self._renderer = Renderer()
        self._leaderboard = Leaderboard()
        self._seed: int = int(time.time())
        self._new_game()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _new_game(self, seed: int | None = None) -> None:
        if seed is None:
            self._seed = int(time.time())
        self.terrain = Terrain(self._seed)
        lander_x = float(2 * TERRAIN_STEP)   # 100 m from left edge
        lander_y = self.terrain.mean_height + float(INITIAL_ALTITUDE)
        self.lander = Lander(lander_x, lander_y, seed=self._seed)
        self.camera = Camera()
        self.camera.x = lander_x             # anchor left edge at start
        self._state: str = "setup"  # setup | playing | landed | crashed | name_entry
        self._crash_reason: str = ""
        self._player_name: str = ""

    # ------------------------------------------------------------------
    # Async run loop (asyncio.sleep(0) allows pygbag web compatibility)
    # ------------------------------------------------------------------

    async def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # cap physics step to 50 ms

            events = pygame.event.get()
            ctrl = self._input.poll(events)

            if ctrl.quit:
                break

            if self._state == "setup":
                if ctrl.new_terrain or ctrl.restart:
                    self._new_game()
                elif ctrl.throttle > 0.0:
                    self._state = "playing"

            elif self._state == "playing":
                self.lander.update(dt, ctrl.throttle, ctrl.torque_cmd)
                self._check_collision()
                alt = self.lander.y - self.terrain.height_at(self.lander.x)
                self.camera.track(self.lander.x, self.lander.y, alt)

            elif self._state == "name_entry":
                self._handle_name_input(events)

            else:  # landed | crashed
                if ctrl.restart or ctrl.new_terrain:
                    self._new_game()

            self._renderer.draw(
                self.screen, self.terrain, self.lander, self.camera,
                self._state, self._crash_reason,
                self._leaderboard, self._player_name,
            )
            pygame.display.flip()

            await asyncio.sleep(0)

        pygame.quit()

    # ------------------------------------------------------------------
    # Name entry
    # ------------------------------------------------------------------

    def _handle_name_input(self, events: list) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    self._leaderboard.add(self._player_name, self.lander.m_fuel)
                    self._state = "landed"
                elif event.key == pygame.K_ESCAPE:
                    # Skip name entry without saving
                    self._state = "landed"
                elif event.key == pygame.K_BACKSPACE:
                    self._player_name = self._player_name[:-1]
                elif event.unicode.isprintable() and len(self._player_name) < _MAX_NAME_LEN:
                    self._player_name += event.unicode

    # ------------------------------------------------------------------
    # Collision / landing detection
    # ------------------------------------------------------------------

    def _check_collision(self) -> None:
        terrain_h = self.terrain.height_at(self.lander.x)

        # Out-of-terrain-bounds → crash
        if self.lander.x < 0:
            self._state = "crashed"
            self._crash_reason = "FLEW OFF LEFT EDGE"
            self.lander.alive = False
            return
        if self.lander.x > TERRAIN_WIDTH:
            self._state = "crashed"
            self._crash_reason = "FLEW OFF RIGHT EDGE"
            self.lander.alive = False
            return

        # Lander has not reached the surface yet (foot pads are LANDER_GROUND_OFFSET_M below centre)
        if self.lander.y > terrain_h + LANDER_GROUND_OFFSET_M + 2.0:
            return

        on_pad = self.terrain.is_on_pad(self.lander.x)

        if on_pad and self.lander.vert_speed <= SAFE_VERT_SPEED:
            self.lander.landed = True
            self.lander.on_pad = True
            score = self.lander.m_fuel
            if self._leaderboard.qualifies(score):
                self._state = "name_entry"
            else:
                self._state = "landed"
        elif not on_pad:
            self._state = "crashed"
            self._crash_reason = "MISSED LANDING PAD"
            self.lander.alive = False
        else:
            self._state = "crashed"
            self._crash_reason = f"IMPACT TOO HARD  {self.lander.vert_speed:.1f} M/S"
            self.lander.alive = False
