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
MOON_GRAVITY = 3.0      # 1.62     # m/s²
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
SAFE_ANGLE = 20.0       # degrees max tilt from vertical at touchdown (MEDIUM)

# Terrain
TERRAIN_WIDTH = 120_000  # meters total width
TERRAIN_STEP = 50        # meters between height samples
TERRAIN_AMPLITUDE = 5000  # meters peak variation
PAD_WIDTH = 300          # meters, flat landing pad width
N_PADS = 4               # number of landing pads

# Initial lander state
INITIAL_ALTITUDE = 10_000   # meters above mean terrain
INITIAL_SPEED_MIN = 60.0    # m/s
INITIAL_SPEED_MAX = 180.0   # m/s
INITIAL_FPA_RANGE = 45.0    # max degrees below horizontal (always descending)
INITIAL_THETA_RANGE = 25.0  # ± degrees initial attitude

# Worldwide leaderboard (Supabase). Leave blank to disable; see supabase/README.md.
# The anon key is meant to be public — row-level security limits it to adding scores.
WORLD_LEADERBOARD_URL = "https://xvoencfjsdbywhhdkuel.supabase.co"
# Project Settings → API Keys → publishable (or legacy anon) key
WORLD_LEADERBOARD_KEY = "sb_publishable_rUkbNBpXOWVd0Qf-agmpFg_KPmSy65Y"

# Audio
AMBIENT_VOLUME = 0.15   # 0.0–1.0, background drone volume during play

# Camera
FIELD_OF_VIEW = 5_000          # horizontal world width visible on screen (metres)
ZOOM_FIXED = SCREEN_W / FIELD_OF_VIEW  # derived — do not set manually
LANDER_SCREEN_Y_FRAC = 0.30   # lander sits at this fraction from top

# Lander geometry — art is drawn in normalised units (centre at origin, y up)
LANDER_ART_SCALE_M = 50.0       # nominal world metres per normalised art unit
LANDER_MIN_PX = 28              # minimum pixels per art unit — keeps lander readable
# Effective world metres per art unit as actually drawn; collision uses the same scale
LANDER_DRAW_SCALE_M = max(LANDER_MIN_PX / ZOOM_FIXED, LANDER_ART_SCALE_M)
LANDER_FOOT_X_ART = 0.88        # foot-pad centre, ± horizontal offset
LANDER_FOOT_Y_ART = -0.80       # foot-pad centre, vertical offset
LANDER_FOOT_R_ART = 0.10        # foot-pad radius
# Upright distance from lander.y down to the bottom of the foot pads (derived)
LANDER_GROUND_OFFSET_M = (-LANDER_FOOT_Y_ART + LANDER_FOOT_R_ART) * LANDER_DRAW_SCALE_M
