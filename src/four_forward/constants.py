# Screen
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
TITLE = "FOUR FORWARD"

# Colors — retro phosphor-green on black
COLOR_BG = (0, 0, 0)
COLOR_GREEN = (57, 255, 20)       # fluorescent green — main graphics
COLOR_GREEN_MID = (30, 160, 10)   # terrain, secondary elements
COLOR_GREEN_DIM = (12, 60, 4)     # stars, background details

# Physics — lander parameters (physical units throughout)
MOON_GRAVITY = 1.62     # m/s²
G0 = 9.81               # m/s², standard gravity (used in Isp→mass-flow conversion)

# Lander mass budget
DRY_MASS = 500.0        # kg
FUEL_MASS = 500.0       # kg  (initial propellant load)

# Propulsion
MAX_THRUST = 12_500.0   # N   (Tmax / m_total_initial ≈ 12.5 m/s²)
ISP = 310.0             # s   (specific impulse, hypergolic-ish)
# Mass-flow rate at full throttle: Tmax / (g0 * Isp)
MDOT_MAX = MAX_THRUST / (G0 * ISP)  # ≈ 4.11 kg/s

# Rotational dynamics
MOI = 1_000.0           # kg⋅m², moment of inertia
MAX_TORQUE = 2_000.0    # N⋅m  (reaction control authority)
OMEGA_DAMPING = 1_000.0 # N⋅m⋅s, angular rate damping
OMEGA_MAX = 4.0         # rad/s, hard clamp (~229 °/s)

# Safe landing thresholds
SAFE_VERT_SPEED = 10.0  # m/s max downward speed for successful pad landing
SAFE_HORZ_SPEED = 6.0   # m/s max horizontal speed
SAFE_ANGLE = 15.0       # degrees max tilt from vertical

# Terrain
TERRAIN_WIDTH = 120_000  # meters total width
TERRAIN_STEP = 50        # meters between height samples
TERRAIN_AMPLITUDE = 1400  # meters peak variation
PAD_WIDTH = 300          # meters, flat landing pad width
N_PADS = 4               # number of landing pads

# Initial lander state
INITIAL_ALTITUDE = 10_000   # meters above mean terrain
INITIAL_SPEED_MIN = 60.0    # m/s
INITIAL_SPEED_MAX = 180.0   # m/s
INITIAL_FPA_RANGE = 45.0    # max degrees below horizontal (always descending)
INITIAL_THETA_RANGE = 25.0  # ± degrees initial attitude

# Camera zoom (pixels per meter)
ZOOM_MIN = 0.01
ZOOM_MAX = 0.8
LANDER_SCREEN_Y_FRAC = 0.30   # lander sits at this fraction from top
ZOOM_ALT_FRAC = 0.55           # altitude occupies this fraction of screen height
