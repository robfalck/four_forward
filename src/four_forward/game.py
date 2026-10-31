"""Main game loop."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pygame

from .camera import Camera
from .constants import (
    AMBIENT_VOLUME,
    FPS,
    INITIAL_ALTITUDE,
    SCREEN_H,
    SCREEN_W,
    TERRAIN_STEP,
    TERRAIN_WIDTH,
    TITLE,
)
from .controls import InputHandler
from .difficulty import DEFAULT_DIFFICULTY, DIFFICULTIES
from .lander import Lander
from .leaderboard import Leaderboard
from .renderer import Renderer
from .terrain import Terrain
from .world_leaderboard import WorldLeaderboard

_AMBIENT_PATH = Path(__file__).parent / "assets" / "ambient_loop.ogg"
_MAX_NAME_LEN = 16
_DIFFICULTY_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
_MENU_UP_KEYS = (pygame.K_UP, pygame.K_w)
_MENU_DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
_MENU_CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self._input = InputHandler()
        self._renderer = Renderer()
        self._leaderboard = Leaderboard()
        self._world = WorldLeaderboard()
        self._last_name = ""  # pre-fills the name prompt on later landings
        self._leaderboard_return = "setup"  # screen to go back to from the leaderboard
        self._seed: int = int(time.time())
        self._difficulty = DEFAULT_DIFFICULTY
        self._prev_throttle = 0.0  # launch only on a fresh thrust press
        self._ambient_loaded = False
        if _AMBIENT_PATH.exists():
            pygame.mixer.music.load(str(_AMBIENT_PATH))
            pygame.mixer.music.set_volume(AMBIENT_VOLUME)
            self._ambient_loaded = True
        self._new_game()
        self._state = "splash"  # override setup; show splash first

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _new_game(self, seed: int | None = None) -> None:
        if seed is None:
            self._seed = int(time.time())
        self.terrain = Terrain(self._seed, self._difficulty.pad_width)
        lander_x = float(2 * TERRAIN_STEP)   # 100 m from left edge
        lander_y = self.terrain.mean_height + float(INITIAL_ALTITUDE)
        self.lander = Lander(lander_x, lander_y, seed=self._seed)
        self.camera = Camera()
        self.camera.track(lander_x, lander_y, float(INITIAL_ALTITUDE))  # frame lander pre-launch
        # splash|difficulty|setup|playing|landed|crashed|name_entry|leaderboard
        self._state: str = "setup"
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

            # Esc skips the name prompt rather than quitting; closing the window always quits
            window_closed = any(e.type == pygame.QUIT for e in events)
            if window_closed or (ctrl.quit and self._state != "name_entry"):
                break

            prev_state = self._state
            pressed_l = any(e.type == pygame.KEYDOWN and e.key == pygame.K_l for e in events)

            if self._state == "splash":
                if pressed_l:
                    self._open_leaderboard()
                elif any(e.type == pygame.KEYDOWN for e in events):
                    self._state = "difficulty"

            elif self._state == "difficulty":
                if pressed_l:
                    self._open_leaderboard()
                else:
                    self._handle_difficulty_menu(events)

            elif self._state == "setup":
                picked = [
                    DIFFICULTIES[_DIFFICULTY_KEYS[e.key]]
                    for e in events
                    if e.type == pygame.KEYDOWN and e.key in _DIFFICULTY_KEYS
                ]
                if ctrl.new_terrain or ctrl.restart:
                    self._new_game()
                elif picked:
                    # Same terrain and start conditions, just resized pads
                    self._difficulty = picked[-1]
                    self._new_game(seed=self._seed)
                elif ctrl.throttle > 0.0 and self._prev_throttle == 0.0:
                    self._state = "playing"
                elif pressed_l:
                    self._open_leaderboard()

            elif self._state == "leaderboard":
                if any(e.type == pygame.KEYDOWN for e in events):
                    self._state = self._leaderboard_return

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

            self._prev_throttle = ctrl.throttle

            if self._ambient_loaded:
                if prev_state != "playing" and self._state == "playing":
                    pygame.mixer.music.play(loops=-1)
                elif prev_state == "playing" and self._state != "playing":
                    pygame.mixer.music.stop()

            self._renderer.draw(
                self.screen, self.terrain, self.lander, self.camera,
                self._state, self._crash_reason,
                self._leaderboard, self._player_name,
                self._difficulty, self._world,
            )
            pygame.display.flip()

            await asyncio.sleep(0)

        pygame.quit()

    def _open_leaderboard(self) -> None:
        self._leaderboard_return = self._state
        self._state = "leaderboard"
        self._world.refresh()

    # ------------------------------------------------------------------
    # Difficulty menu
    # ------------------------------------------------------------------

    def _handle_difficulty_menu(self, events: list) -> None:
        idx = DIFFICULTIES.index(self._difficulty)
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in _MENU_UP_KEYS:
                idx = (idx - 1) % len(DIFFICULTIES)
            elif event.key in _MENU_DOWN_KEYS:
                idx = (idx + 1) % len(DIFFICULTIES)
            elif event.key in _DIFFICULTY_KEYS:
                idx = _DIFFICULTY_KEYS[event.key]
                self._difficulty = DIFFICULTIES[idx]
                self._new_game(seed=self._seed)  # → setup
                return
            elif event.key in _MENU_CONFIRM_KEYS:
                self._difficulty = DIFFICULTIES[idx]
                self._new_game(seed=self._seed)  # → setup
                return
        # Cursor tracks the highlighted choice; terrain is rebuilt on confirm
        self._difficulty = DIFFICULTIES[idx]

    # ------------------------------------------------------------------
    # Name entry
    # ------------------------------------------------------------------

    def _handle_name_input(self, events: list) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    name = self._player_name.strip() or "UNKNOWN"
                    score = self.lander.m_fuel
                    if self._leaderboard.qualifies(score):
                        self._leaderboard.add(name, score, self._difficulty.name)
                    self._world.submit(name, score, self._difficulty.name)
                    self._last_name = name
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

        # Touchdown when the bottom of either foot pad (or the body centre, if
        # inverted) reaches the terrain directly beneath it.
        contacts = self.lander.foot_contacts() + [(self.lander.x, self.lander.y)]
        clearance = min(
            cy - self.terrain.height_at(min(max(cx, 0.0), TERRAIN_WIDTH))
            for cx, cy in contacts
        )
        if clearance > 0.0:
            return

        on_pad = self.terrain.is_on_pad(self.lander.x)

        if on_pad and self.lander.vert_speed <= self._difficulty.safe_vert_speed:
            # Rest the feet on the surface rather than slightly below it
            self.lander.raise_by(-clearance)
            self.lander.landed = True
            self.lander.on_pad = True
            score = self.lander.m_fuel
            self._world.submit_status = ""
            # Ask for a name whenever the score can go on either leaderboard
            if self._leaderboard.qualifies(score) or self._world.enabled:
                self._player_name = self._last_name
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
