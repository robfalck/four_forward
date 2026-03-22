"""
Lander equations of motion in continuous state-space form.

State vector  s  (shape [7], float64)
  s[0] = x       position (m)
  s[1] = y       position (m)
  s[2] = vx      velocity (m/s)
  s[3] = vy      velocity (m/s)
  s[4] = theta   attitude angle (rad), 0 = nose pointing up (+y)
  s[5] = omega   angular rate (rad/s), positive = counter-clockwise
  s[6] = m_fuel  remaining propellant mass (kg)

Control vector  u  (shape [2], float64)
  u[0] = throttle   ∈ [0, 1]   thrust fraction
  u[1] = torque_cmd ∈ [-1, 1]  normalised RCS torque (+1 = CCW = nose left)

The derivative  ds/dt = f(s, u)  is the single source of truth for the
dynamics.  The game integrates it with RK4.  Optimal-control solvers can
use it directly:
  - jax.jacfwd(derivatives, argnums=0)  → A-matrix (∂f/∂s)
  - jax.jacfwd(derivatives, argnums=1)  → B-matrix (∂f/∂u)
  - jax.jit(rk4)                        → fast discrete-time integrator
"""

from __future__ import annotations

import random

import jax
import jax.numpy as jnp
from jax import Array

from .constants import (
    DRY_MASS,
    FUEL_MASS,
    INITIAL_FPA_RANGE,
    INITIAL_SPEED_MAX,
    INITIAL_SPEED_MIN,
    INITIAL_THETA_RANGE,
    MAX_THRUST,
    MAX_TORQUE,
    MDOT_MAX,
    MOI,
    MOON_GRAVITY,
    OMEGA_DAMPING,
    OMEGA_MAX,
)

# Enable 64-bit floats for numerical accuracy (trajectory optimisation needs this)
jax.config.update("jax_enable_x64", True)

# State indices — use these everywhere instead of magic numbers
IX = 0   # x position
IY = 1   # y position
IVX = 2  # x velocity
IVY = 3  # y velocity
ITH = 4  # theta (attitude, rad)
IOM = 5  # omega (angular rate, rad/s)
IFU = 6  # m_fuel (kg)


# ---------------------------------------------------------------------------
# ODE right-hand side — pure JAX, JIT-compilable, differentiable
# ---------------------------------------------------------------------------

def derivatives(s: Array, u: Array) -> Array:
    """
    Compute ds/dt = f(s, u).

    Pure function; does not modify s.  Both s and u must be JAX arrays.
    This function can be passed directly to scipy / casadi / diffrax etc.
    """
    throttle = jnp.clip(u[0], 0.0, 1.0)
    torque_cmd = jnp.clip(u[1], -1.0, 1.0)

    m_total = DRY_MASS + jnp.maximum(0.0, s[IFU])
    has_fuel = jnp.where(s[IFU] > 0.0, 1.0, 0.0)
    thrust = MAX_THRUST * throttle * has_fuel

    ax = -(thrust / m_total) * jnp.sin(s[ITH])
    ay = (thrust / m_total) * jnp.cos(s[ITH]) - MOON_GRAVITY

    # Rotational dynamics: torque drives omega, linear damping resists spin
    alpha = (MAX_TORQUE * torque_cmd - OMEGA_DAMPING * s[IOM]) / MOI

    m_fuel_dot = -MDOT_MAX * throttle * has_fuel

    return jnp.array([s[IVX], s[IVY], ax, ay, s[IOM], alpha, m_fuel_dot])


# ---------------------------------------------------------------------------
# RK4 integrator — JIT-compiled for game use, also usable in solvers
# ---------------------------------------------------------------------------

@jax.jit
def rk4(s: Array, u: Array, dt: float) -> Array:
    """One RK4 step of the continuous dynamics."""
    k1 = derivatives(s, u)
    k2 = derivatives(s + 0.5 * dt * k1, u)
    k3 = derivatives(s + 0.5 * dt * k2, u)
    k4 = derivatives(s + dt * k3, u)
    return s + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


# ---------------------------------------------------------------------------
# Game-facing lander object
# ---------------------------------------------------------------------------

class Lander:
    """Wraps the ODE state vector with game-friendly properties and update loop."""

    def __init__(self, x: float, y: float, seed: int | None = None) -> None:
        rng = random.Random(seed)
        import math

        speed = rng.uniform(INITIAL_SPEED_MIN, INITIAL_SPEED_MAX)
        fpa = math.radians(rng.uniform(-INITIAL_FPA_RANGE, -5.0))  # always descending
        vx = max(speed * math.cos(fpa), 10.0)  # always moving right, at least 10 m/s
        vy = speed * math.sin(fpa)
        theta = math.radians(rng.uniform(-INITIAL_THETA_RANGE, INITIAL_THETA_RANGE))

        self.state: Array = jnp.array([x, y, vx, vy, theta, 0.0, FUEL_MASS], dtype=jnp.float64)

        self.alive: bool = True
        self.landed: bool = False
        self.on_pad: bool = False
        self.thrusting: bool = False  # for renderer flame effect

    # ------------------------------------------------------------------
    # Integration
    # ------------------------------------------------------------------

    def update(self, dt: float, throttle: float, torque_cmd: float) -> None:
        """Advance the ODE by dt seconds using RK4."""
        if not self.alive or self.landed:
            return

        u = jnp.array([throttle, torque_cmd], dtype=jnp.float64)
        self.thrusting = bool(throttle > 0.0 and self.state[IFU] > 0.0)

        new_s = rk4(self.state, u, dt)

        # Post-integration hard constraints (not part of ODE, just bounds)
        new_s = new_s.at[IFU].set(jnp.maximum(0.0, new_s[IFU]))
        new_s = new_s.at[IOM].set(jnp.clip(new_s[IOM], -OMEGA_MAX, OMEGA_MAX))

        self.state = new_s

    # ------------------------------------------------------------------
    # Convenience properties (convert JAX scalars → Python floats)
    # ------------------------------------------------------------------

    @property
    def x(self) -> float:
        return float(self.state[IX])

    @property
    def y(self) -> float:
        return float(self.state[IY])

    @property
    def vx(self) -> float:
        return float(self.state[IVX])

    @property
    def vy(self) -> float:
        return float(self.state[IVY])

    @property
    def theta(self) -> float:
        """Attitude angle in radians (0 = nose up)."""
        return float(self.state[ITH])

    @property
    def theta_deg(self) -> float:
        import math
        return math.degrees(float(self.state[ITH]))

    @property
    def omega(self) -> float:
        return float(self.state[IOM])

    @property
    def m_fuel(self) -> float:
        return float(self.state[IFU])

    @property
    def fuel_fraction(self) -> float:
        return float(self.state[IFU]) / FUEL_MASS

    @property
    def speed(self) -> float:
        return float(jnp.hypot(self.state[IVX], self.state[IVY]))

    @property
    def vert_speed(self) -> float:
        """Positive = descending."""
        return -float(self.state[IVY])
