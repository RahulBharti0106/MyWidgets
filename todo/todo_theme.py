"""
Theme constants for the Desktop To-Do widget.
"""

FONT_FAMILY = "Segoe UI"
FONT_SIZE_DEFAULT = 13
FONT_SIZE_DUE_LABEL_OFFSET = -2
FONT_FAMILY_MONO = "Cascadia Code"

DARK = {
    "card_bg": "rgba(28, 28, 32, 0.97)",
    "border": "#1f1f21",
    "card_radius": "18px",
    "text": "#e8e8f0",
    "text_muted": "#F4EEEE",
    "input_bg": "#2a2a35",
    "input_radius": "7px",
    "btn_bg": "#2dab29",
    "btn_hover": "#3b3bc2",
    "btn_radius": "7px",
    "task_bg": "#2a2a2e",
    "task_border": "#3a3a3f",
    "task_radius": "8px",
    "overdue_color": "#ff5555",
    "due_color": "#888888",
    "scroll_track": "#2a2a35",
    "scroll_thumb": "#555555",
    "scroll_bg": "rgba(28,28,32,0)",
}

LIGHT = {
    "card_bg": "rgba(245, 245, 255, 0.97)",
    "border": "#c8c8d8",
    "card_radius": "14px",
    "text": "#1a1a2e",
    "text_muted": "#999999",
    "input_bg": "#ffffff",
    "input_radius": "7px",
    "btn_bg": "#4a80d9",
    "btn_hover": "#2a60b9",
    "btn_radius": "7px",
    "task_bg": "#f0f0f5",
    "task_border": "#dddddd",
    "task_radius": "8px",
    "overdue_color": "#cc2222",
    "due_color": "#777777",
    "scroll_track": "#eeeeee",
    "scroll_thumb": "#bbbbbb",
    "scroll_bg": "rgba(245,245,255,0)",
}

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

DEFAULT_X = 100
DEFAULT_Y = 100
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 480
DEFAULT_OPACITY = 0.92
DEFAULT_DARK_MODE = True
DEFAULT_STARTUP = True
DEFAULT_LIST_NAME = "Default"

MIN_WIDTH = 240
MIN_HEIGHT = 200
ADD_BTN_SIZE = 30
DELETE_BTN_SIZE = 20
SETTINGS_BTN_SIZE = 24

SAVE_INTERVAL_MS = 5000
REMINDER_INTERVAL_MS = 60_000
REMINDER_EARLY_WARNING_SECONDS = 300


def get_theme(dark: bool) -> dict:
    return DARK if dark else LIGHT


def get_dialog_theme(dark: bool) -> dict:
    return DIALOG_DARK if dark else DIALOG_LIGHT

