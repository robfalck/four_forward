"""Main game loop."""

from __future__ import annotations

import asyncio
import time

import pygame

from .camera import Camera
from .constants import (
    FPS,
    INITIAL_ALTITUDE,
    SAFE_VERT_SPEED,
    SCREEN_H,
    SCREEN_W,
    TERRAIN_STEP,
    TERRAIN_WIDTH,
    TITLE,
)
from .controls import InputHandler
from .lander import Lander
from .renderer import Renderer
from .terrain import Terrain


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self._input = InputHandler()
        self._renderer = Renderer()
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
        self._state: str = "setup"  # setup | playing | landed | crashed

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
            else:  # landed | crashed
                if ctrl.restart or ctrl.new_terrain:
                    self._new_game()

            self._renderer.draw(self.screen, self.terrain, self.lander, self.camera, self._state)
            pygame.display.flip()

            await asyncio.sleep(0)

        pygame.quit()

    # ------------------------------------------------------------------
    # Collision / landing detection
    # ------------------------------------------------------------------

    def _check_collision(self) -> None:
        terrain_h = self.terrain.height_at(self.lander.x)

        # Out-of-terrain-bounds → crash
        if self.lander.x < 0 or self.lander.x > TERRAIN_WIDTH:
            self._state = "crashed"
            self.lander.alive = False
            return

        # Lander has not reached the surface yet
        if self.lander.y > terrain_h + 2.0:
            return

        on_pad = self.terrain.is_on_pad(self.lander.x)

        if on_pad and self.lander.vert_speed <= SAFE_VERT_SPEED:
            self._state = "landed"
            self.lander.landed = True
            self.lander.on_pad = True
        else:
            self._state = "crashed"
            self.lander.alive = False
