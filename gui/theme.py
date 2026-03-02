"""
gui/theme.py
------------
Design system — colors, fonts, sizes.
Aesthetic: Dark tech with rose-gold & cyan accents.
Clean, precise, unapologetically sharp.
"""

# ──────────────────────────────────────────────
# Base Palette
# ──────────────────────────────────────────────

BG_DEEP     = (10,  10,  18)      # near-black base
BG_PANEL    = (16,  16,  28)      # sidebar / panel
BG_CARD     = (22,  22,  38)      # card / section
BG_INPUT    = (28,  28,  48)      # input fields
BORDER      = (40,  40,  70)      # subtle borders

# Accent – rose gold
ACCENT_ROSE = (255, 150, 150)     # headings, hover
ACCENT_PINK = (230, 100, 140)     # active / selected

# Accent – tech cyan
ACCENT_CYAN = (100, 220, 220)     # start node, info
ACCENT_TEAL = ( 60, 190, 180)     # secondary

# Semantic grid colors
COLOR_EMPTY    = (22,  22,  38)
COLOR_WALL     = (45,  45,  75)
COLOR_START    = ( 80, 220, 180)   # teal-green
COLOR_GOAL     = (255, 140, 160)   # rose
COLOR_FRONTIER = (255, 215,  80)   # amber-yellow
COLOR_VISITED  = ( 80, 120, 200)   # indigo-blue
COLOR_PATH     = (140, 255, 140)   # mint green
COLOR_AGENT    = (255, 255, 100)   # bright yellow agent dot

# Dynamic mode specific
COLOR_TRAIL          = (130,  90, 200)   # violet — cells already walked
COLOR_REPLAN_VISITED = ( 80, 180, 255)   # bright cyan — replan expansion
COLOR_REPLAN_PATH    = (255, 220,  60)   # gold — newly computed path flash

# Text
TEXT_PRIMARY   = (230, 230, 245)
TEXT_SECONDARY = (140, 140, 175)
TEXT_MUTED     = ( 80,  80, 115)
TEXT_ACCENT    = ACCENT_ROSE

# Buttons
BTN_NORMAL     = (35,  35,  60)
BTN_HOVER      = (50,  50,  85)
BTN_ACTIVE     = ACCENT_PINK
BTN_DISABLED   = (25,  25,  42)

BTN_TEXT_NORMAL   = TEXT_PRIMARY
BTN_TEXT_ACTIVE   = (255, 255, 255)
BTN_TEXT_DISABLED = TEXT_MUTED

# ──────────────────────────────────────────────
# Geometry
# ──────────────────────────────────────────────

WINDOW_W      = 1280
WINDOW_H      = 820
SIDEBAR_W     = 290
GRID_PADDING  = 14
GRID_PAD_BOT  = 28      # extra bottom padding so legend strip doesn't overlap grid
CORNER_RADIUS = 6

# ──────────────────────────────────────────────
# Fonts (loaded in renderer, defined here as sizes)
# ──────────────────────────────────────────────

FONT_SM  = 12
FONT_MD  = 15
FONT_LG  = 18
FONT_XL  = 22
FONT_XXL = 28

# ──────────────────────────────────────────────
# Animation speeds
# ──────────────────────────────────────────────

VIZ_STEP_DELAY_MS   = 18    # ms between search steps during visualization
AGENT_STEP_DELAY_MS = 80    # ms between agent movement steps
SPAWN_PROBABILITY   = 0.08  # chance per agent step for new obstacle in dynamic mode
