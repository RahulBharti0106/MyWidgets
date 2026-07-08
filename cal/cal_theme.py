FONT_FAMILY = "Segoe UI"
DEFAULT_OPACITY = 0.92
DEFAULT_DARK_MODE = True
DEFAULT_STARTUP = True

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

CAL_DARK = {
    "day_bg": "#1e1e22",
    "day_bg_hover": "#2e2e3a",
    "day_text": "#e8e8f0",
    "day_text_muted": "#555566",
    "today_bg": "#27ae60",
    "today_text": "#f9fafa",
    "past_bg": "#8D0808",
    "past_text": "#080000",
    "header_bg": "rgba(28,28,32,0.97)",
    "weekday_text": "#068edd",
    "dot_color": "#efdf0a",
    "nav_btn": "#2a2a3a",
    "nav_btn_hover": "#3a3a5a",
    "today_btn_bg": "#2a2a3a",
    "today_btn_hover": "#3a3a5a",
    "card_bg": "rgba(22, 22, 26, 0.97)",
    "border": "#3a3a4f",
    "card_radius": "14px",
    "text": "#e8e8f0",
    "text_muted": "#888888",
    "btn_bg": "#3a3a60",
    "btn_hover": "#5050a0",
    "overdue_color": "#ff5555",
}

CAL_LIGHT = {
    "day_bg": "#f8f8ff",
    "day_bg_hover": "#ebebff",
    "day_text": "#1a1a2e",
    "day_text_muted": "#bbbbcc",
    "today_bg": "#27ae60",
    "today_text": "#ffffff",
    "past_bg": "#fde8e8",
    "past_text": "#cc2222",
    "header_bg": "rgba(245,245,255,0.97)",
    "weekday_text": "#8888aa",
    "dot_color": "#2a70d9",
    "nav_btn": "#e0e0f0",
    "nav_btn_hover": "#c8c8e8",
    "today_btn_bg": "#e0e0f0",
    "today_btn_hover": "#c8c8e8",
    "card_bg": "rgba(245,245,255,0.97)",
    "border": "#c8c8d8",
    "card_radius": "14px",
    "text": "#1a1a2e",
    "text_muted": "#999999",
    "btn_bg": "#4a80d9",
    "btn_hover": "#2a60b9",
    "overdue_color": "#cc2222",
}


def get_cal_theme(dark: bool) -> dict:
    return CAL_DARK if dark else CAL_LIGHT


def get_dialog_theme(dark: bool) -> dict:
    return DIALOG_DARK if dark else DIALOG_LIGHT

