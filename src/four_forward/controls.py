"""Input handling: keyboard, mouse axis, and joystick."""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class ControlState:
    throttle: float = 0.0     # [0, 1]
    torque_cmd: float = 0.0   # [-1, 1]; +1 = CCW (nose left), -1 = CW (nose right)
    restart: bool = False
    new_terrain: bool = False
    quit: bool = False


class InputHandler:
    def __init__(self) -> None:
        self._joystick: pygame.joystick.Joystick | None = None
        self._init_joystick()
        # Joystick axis assignments (user-configurable)
        self.joy_rotate_axis: int = 0   # horizontal axis → torque
        self.joy_thrust_axis: int = 1   # vertical axis → throttle (pull back = thrust)
        self.axis_deadzone: float = 0.15

    def _init_joystick(self) -> None:
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    def poll(self, events: list[pygame.event.Event]) -> ControlState:
        state = ControlState()

        for event in events:
            if event.type == pygame.QUIT:
                state.quit = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    state.restart = True
                elif event.key == pygame.K_n:
                    state.new_terrain = True
                elif event.key == pygame.K_ESCAPE:
                    state.quit = True
            elif event.type == pygame.JOYDEVICEADDED:
                self._init_joystick()
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._joystick = None

        # ---- Keyboard (binary) ----
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            state.throttle = 1.0
        if keys[pygame.K_a]:
            state.torque_cmd += 1.0   # CCW, nose left
        if keys[pygame.K_d]:
            state.torque_cmd -= 1.0   # CW, nose right
        state.torque_cmd = max(-1.0, min(1.0, state.torque_cmd))

        # ---- Mouse axis (hold LMB to steer) ----
        if pygame.mouse.get_pressed()[0]:
            rel_x, _ = pygame.mouse.get_rel()
            if abs(rel_x) > 2:
                # Map mouse drag speed to torque
                state.torque_cmd = max(-1.0, min(1.0, -rel_x / 20.0))
        else:
            pygame.mouse.get_rel()  # consume accumulation to avoid jump

        # ---- Joystick ----
        if self._joystick is not None:
            try:
                x_axis = self._joystick.get_axis(self.joy_rotate_axis)
                y_axis = self._joystick.get_axis(self.joy_thrust_axis)
                if abs(x_axis) > self.axis_deadzone:
                    state.torque_cmd = -x_axis  # left stick left = CCW
                if y_axis < -self.axis_deadzone:  # pull back = thrust
                    norm = (-y_axis - self.axis_deadzone) / (1.0 - self.axis_deadzone)
                    state.throttle = min(1.0, norm)
            except pygame.error:
                self._joystick = None

        return state
