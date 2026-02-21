"""
╔══════════════════════════════════════════════════════════════════╗
║           DESKTOP TO-DO WIDGET — THEME CONFIGURATION            ║
║                                                                  ║
║  Edit this file to change all colors, fonts, and sizes.          ║
║  Colors are hex strings like "#rrggbb" or "rgba(r,g,b,alpha)".   ║
║  No need to touch desktop_widget.py for visual changes.          ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════
#  FONT SETTINGS
# ══════════════════════════════════════════════

# Main font used everywhere in the widget
FONT_FAMILY = "Segoe UI"

# Base font size in points. The title will be this + 1.
# Recommended range: 10 – 18
# This is the DEFAULT — user can also change it via the Settings (⚙) panel at runtime.
FONT_SIZE_DEFAULT = 13

# Font size for due-date labels (shown below task title)
# Usually 2pt smaller than base font
FONT_SIZE_DUE_LABEL_OFFSET = -2  # e.g. if FONT_SIZE_DEFAULT=13, due label = 11

# Code/monospace font (not currently used in widget but here for future)
FONT_FAMILY_MONO = "Cascadia Code"


# ══════════════════════════════════════════════
#  DARK MODE COLORS
#  (used when dark_mode = True in settings)
# ══════════════════════════════════════════════

DARK = {
    # ── Card / Window ─────────────────────────
    # The main frosted-glass card background.
    # Increase alpha (last value) toward 1.0 for more opacity, 0.0 for fully transparent.
    "card_bg": "rgba(28, 28, 32, 0.97)",
    # Border around the card
    "border": "#1f1f21",
    # Border radius of the card (rounded corners). 0 = sharp corners.
    "card_radius": "18px",
    # ── Text ──────────────────────────────────
    # Primary text (task titles, labels)
    "text": "#e8e8f0",
    # Muted/secondary text (e.g. "No tasks — add one above!")
    "text_muted": "#F4EEEE",
    # ── Inputs (text box, dropdowns) ──────────
    # Background of QLineEdit and QComboBox
    "input_bg": "#2a2a35",
    # Border radius of inputs
    "input_radius": "7px",
    # ── Buttons ───────────────────────────────
    # Normal button background (the + and … buttons)
    "btn_bg": "#2dab29",
    # Button color when hovered
    "btn_hover": "#3b3bc2",
    # Button border radius
    "btn_radius": "7px",
    # ── Task Item Cards ───────────────────────
    # Background of each individual task row
    "task_bg": "#2a2a2e",
    # Border of each task row
    "task_border": "#3a3a3f",
    # Border radius of each task row
    "task_radius": "8px",
    # ── Overdue label color ───────────────────
    # Color of the due-date label when the task is past due
    "overdue_color": "#ff5555",
    # Color of the due-date label when task is NOT overdue
    "due_color": "#888888",
    # ── Scrollbar ─────────────────────────────
    # Scrollbar track background
    "scroll_track": "#2a2a35",
    # Scrollbar thumb (the draggable part)
    "scroll_thumb": "#555555",
    # ── Transparent scroll area background ────
    # Keep this transparent so the card background shows through
    "scroll_bg": "rgba(28,28,32,0)",
}


# ══════════════════════════════════════════════
#  LIGHT MODE COLORS
#  (used when dark_mode = False in settings)
# ══════════════════════════════════════════════

LIGHT = {
    # ── Card / Window ─────────────────────────
    "card_bg": "rgba(245, 245, 255, 0.97)",
    "border": "#c8c8d8",
    "card_radius": "14px",
    # ── Text ──────────────────────────────────
    "text": "#1a1a2e",
    "text_muted": "#999999",
    # ── Inputs ────────────────────────────────
    "input_bg": "#ffffff",
    "input_radius": "7px",
    # ── Buttons ───────────────────────────────
    "btn_bg": "#4a80d9",
    "btn_hover": "#2a60b9",
    "btn_radius": "7px",
    # ── Task Item Cards ───────────────────────
    "task_bg": "#f0f0f5",
    "task_border": "#dddddd",
    "task_radius": "8px",
    # ── Overdue / Due labels ──────────────────
    "overdue_color": "#cc2222",
    "due_color": "#777777",
    # ── Scrollbar ─────────────────────────────
    "scroll_track": "#eeeeee",
    "scroll_thumb": "#bbbbbb",
    "scroll_bg": "rgba(245,245,255,0)",
}


# ══════════════════════════════════════════════
#  DIALOG / SETTINGS PANEL COLORS
#  (the popup when you click ⚙ or add a task)
# ══════════════════════════════════════════════

DIALOG_DARK = {
    "bg": "#1e1e21",
    "text": "#e8e8e8",
    "input_bg": "#2a2a2e",
    "border": "#444444",
    "btn_bg": "#3a3a5e",
    "btn_hover": "#5555aa",
}

DIALOG_LIGHT = {
    "bg": "#ffffff",
    "text": "#222222",
    "input_bg": "#f5f5f5",
    "border": "#cccccc",
    "btn_bg": "#4a90d9",
    "btn_hover": "#357abd",
}


# ══════════════════════════════════════════════
#  WIDGET WINDOW DEFAULTS
#  (used on first launch; after that, position
#   and size are remembered from settings.json)
# ══════════════════════════════════════════════

# Default position (pixels from top-left of screen)
DEFAULT_X = 100
DEFAULT_Y = 100

# Default size in pixels
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 480

# Default opacity (0.0 = invisible, 1.0 = fully opaque)
# User can adjust this in the Settings panel at runtime.
DEFAULT_OPACITY = 0.92

# Whether dark mode is on by default on first launch
DEFAULT_DARK_MODE = True

# Whether to auto-launch at Windows startup by default
DEFAULT_STARTUP = True

# Default task list name shown on first launch
DEFAULT_LIST_NAME = "Default"


# ══════════════════════════════════════════════
#  SIZING CONSTANTS
# ══════════════════════════════════════════════

# Minimum widget size — prevents collapsing to unusable dimensions
MIN_WIDTH = 240
MIN_HEIGHT = 200

# Height and width of the + and … buttons (pixels)
ADD_BTN_SIZE = 30

# Size of the ✕ delete button on each task row
DELETE_BTN_SIZE = 20

# Size of the ⚙ settings button in the header
SETTINGS_BTN_SIZE = 24

# ══════════════════════════════════════════════
#  TIMING
# ══════════════════════════════════════════════

# How often (in milliseconds) the widget saves its position/size to disk.
# Lower = more frequent saves (safer but slightly more disk I/O)
SAVE_INTERVAL_MS = 5000  # 5 seconds

# How often (in milliseconds) the reminder checker runs.
# 60000 = every 1 minute. Minimum sensible value is 30000.
REMINDER_INTERVAL_MS = 60_000  # 1 minute

# How many seconds before a due time to show a "due soon" warning
REMINDER_EARLY_WARNING_SECONDS = 300  # 5 minutes


# ══════════════════════════════════════════════
#  HELPER — used by desktop_widget.py
# ══════════════════════════════════════════════


def get_theme(dark: bool) -> dict:
    """Return the correct color dict based on dark/light mode."""
    return DARK if dark else LIGHT


def get_dialog_theme(dark: bool) -> dict:
    """Return dialog colors based on dark/light mode."""
    return DIALOG_DARK if dark else DIALOG_LIGHT
