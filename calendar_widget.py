"""
Windows Desktop Calendar Widget  ·  v1.0
Stack : Python + PyQt6

Companion to desktop_widget.py — shares theme_config.py for all colors.

Features:
  • macOS-style dark calendar on the desktop layer
  • Past dates: red background + strikethrough
  • Today: green highlight
  • Future dates with task due dots (reads tasks.json from the to-do widget)
  • Navigation: < prev  [Month Year click-to-jump]  next >  [Today]
  • Draggable, resizable, persists position across restarts
  • Dark / Light mode via theme_config.py
  • Sits behind all windows (desktop layer), starts with Windows
"""

import sys
import json
import os
import calendar
import threading
from datetime import date, datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QSystemTrayIcon,
    QMenu,
    QDialog,
    QComboBox,
    QSizeGrip,
    QSlider,
    QCheckBox,
    QGridLayout,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QDate, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QAction, QCursor, QFontMetrics

import theme_config as TC


# ─────────────────────────────────────────────
# Paths — reads tasks from the to-do widget
# ─────────────────────────────────────────────
APP_NAME = "DesktopCalendar"
TODO_APP_NAME = "DesktopTodo"

DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / APP_NAME
SETTINGS_FILE = DATA_DIR / "settings.json"
TODO_TASKS = Path(os.getenv("APPDATA", Path.home())) / TODO_APP_NAME / "tasks.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DAYS_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# ── Calendar-specific palette additions ──────────────────────────────────────
# These extend theme_config — edit here to tweak calendar-only colors.

CAL_DARK = {
    "day_bg": "#1e1e22",  # normal day cell background
    "day_bg_hover": "#2e2e3a",  # hover
    "day_text": "#e8e8f0",  # normal day number
    "day_text_muted": "#555566",  # days from adjacent months
    "today_bg": "#27ae60",  # today highlight (green)
    "today_text": "#ffffff",
    "past_bg": "#4a1a1a",  # past date background (red-tinted)
    "past_text": "#cc4444",  # past date text (red)
    "header_bg": "rgba(28,28,32,0.97)",
    "weekday_text": "#8888aa",  # Sun Mon Tue ...
    "dot_color": "#5b9cf6",  # task-due indicator dot
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
}


def get_cal_theme(dark: bool) -> dict:
    return CAL_DARK if dark else CAL_LIGHT


# ─────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────
class CalStorage:
    _lock = threading.Lock()

    @staticmethod
    def load_settings() -> dict:
        defaults = {
            "x": 460,
            "y": 100,
            "width": 380,
            "height": 400,
            "dark_mode": TC.DEFAULT_DARK_MODE,
            "opacity": TC.DEFAULT_OPACITY,
            "startup": TC.DEFAULT_STARTUP,
        }
        if not SETTINGS_FILE.exists():
            return defaults
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            defaults.update(loaded)
            return defaults
        except Exception:
            return defaults

    @staticmethod
    def save_settings(s: dict):
        with CalStorage._lock:
            tmp = SETTINGS_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2)
            tmp.replace(SETTINGS_FILE)

    @staticmethod
    def load_due_dates() -> set:
        """Return a set of date objects that have at least one task due."""
        if not TODO_TASKS.exists():
            return set()
        try:
            with open(TODO_TASKS, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = set()
            for t in data.get("tasks", []):
                if t.get("due") and not t.get("completed", False):
                    try:
                        d = datetime.fromisoformat(t["due"]).date()
                        result.add(d)
                    except ValueError:
                        pass
            return result
        except Exception:
            return set()


# ─────────────────────────────────────────────
# Startup Manager  (shared logic)
# ─────────────────────────────────────────────
class StartupManager:
    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_KEY = APP_NAME

    @staticmethod
    def enable():
        try:
            import winreg

            exe = (
                sys.executable
                if getattr(sys, "frozen", False)
                else f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            )
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                StartupManager.REG_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe)
        except Exception:
            pass

    @staticmethod
    def disable():
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                StartupManager.REG_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, APP_NAME)
        except Exception:
            pass

    @staticmethod
    def is_enabled() -> bool:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, StartupManager.REG_KEY
            ) as key:
                winreg.QueryValueEx(key, APP_NAME)
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────
# Jump-to Dialog  (click on month/year label)
# ─────────────────────────────────────────────
class JumpDialog(QDialog):
    def __init__(self, current_year: int, current_month: int, dark: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Go to month")
        self.setFixedWidth(260)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self._build_ui(current_year, current_month)
        self._style(dark)

    def _build_ui(self, year, month):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        row = QHBoxLayout()

        self.month_combo = QComboBox()
        for i, m in enumerate(
            [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ],
            1,
        ):
            self.month_combo.addItem(m, i)
        self.month_combo.setCurrentIndex(month - 1)
        row.addWidget(self.month_combo, stretch=2)

        self.year_combo = QComboBox()
        today = date.today()
        for y in range(today.year - 10, today.year + 11):
            self.year_combo.addItem(str(y), y)
        self.year_combo.setCurrentText(str(year))
        row.addWidget(self.year_combo, stretch=1)

        layout.addLayout(row)

        btns = QHBoxLayout()
        ok = QPushButton("Go")
        ok.clicked.connect(self.accept)
        can = QPushButton("Cancel")
        can.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(can)
        layout.addLayout(btns)

    def _style(self, dark: bool):
        t = TC.get_dialog_theme(dark)
        self.setStyleSheet(
            f"""
            QDialog {{ background: {t["bg"]}; color: {t["text"]}; }}
            QLabel  {{ color: {t["text"]}; background: transparent; }}
            QComboBox {{
                background: {t["input_bg"]}; color: {t["text"]};
                border: 1px solid {t["border"]}; border-radius: 6px; padding: 5px;
            }}
            QPushButton {{
                background: {t["btn_bg"]}; color: white;
                border-radius: 6px; padding: 7px 16px; border: none;
            }}
            QPushButton:hover {{ background: {t["btn_hover"]}; }}
        """
        )

    def get_result(self):
        return (self.year_combo.currentData(), self.month_combo.currentData())


# ─────────────────────────────────────────────
# Settings Panel
# ─────────────────────────────────────────────
class SettingsPanel(QDialog):
    def __init__(self, settings: dict, dark: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calendar Settings")
        self.setFixedWidth(290)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self._build_ui(settings, dark)

    def _build_ui(self, settings, dark):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel("Opacity:"))
        self.opacity_sl = QSlider(Qt.Orientation.Horizontal)
        self.opacity_sl.setRange(30, 100)
        self.opacity_sl.setValue(int(settings.get("opacity", 0.92) * 100))
        layout.addWidget(self.opacity_sl)

        self.dark_chk = QCheckBox("Dark Mode")
        self.dark_chk.setChecked(settings.get("dark_mode", True))
        layout.addWidget(self.dark_chk)

        self.startup_chk = QCheckBox("Launch at Windows startup")
        self.startup_chk.setChecked(StartupManager.is_enabled())
        layout.addWidget(self.startup_chk)

        ok = QPushButton("Apply & Close")
        ok.clicked.connect(self.accept)
        layout.addWidget(ok)

        t = TC.get_dialog_theme(dark)
        self.setStyleSheet(
            f"""
            QDialog {{ background: {t["bg"]}; color: {t["text"]}; }}
            QLabel, QCheckBox {{ color: {t["text"]}; background: transparent; }}
            QPushButton {{
                background: {t["btn_bg"]}; color: white;
                border-radius: 6px; padding: 8px; border: none;
            }}
            QPushButton:hover {{ background: {t["btn_hover"]}; }}
        """
        )

    def get_result(self):
        return {
            "opacity": self.opacity_sl.value() / 100,
            "dark_mode": self.dark_chk.isChecked(),
            "startup": self.startup_chk.isChecked(),
        }


# ─────────────────────────────────────────────
# Day Cell  — scales with widget size
# ─────────────────────────────────────────────
class DayCell(QFrame):
    """
    A single calendar day cell.

    Sizing: cells use Expanding policy so the grid fills all available
    space. Font size is passed in from the parent (computed from widget
    width) so everything scales together when the user resizes.

    Task dot: a small circular QLabel pinned to the top-right corner
    via absolute positioning inside the cell frame.
    """

    def __init__(
        self,
        day: int,
        this_month: bool,
        is_today: bool,
        is_past: bool,
        has_task: bool,
        theme: dict,
        font_size: int,
    ):
        super().__init__()
        self._day = day
        self._this_month = this_month
        self._is_today = is_today
        self._is_past = is_past
        self._has_task = has_task
        self._theme = theme
        self._font_size = font_size

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(28, 28)
        self._dot = None  # always exists before _build() or resizeEvent runs
        self._build()

    def _build(self):
        t = self._theme
        fs = self._font_size

        if not self._day:
            self.setStyleSheet("background: transparent; border: none;")
            return

        # ── colours ──────────────────────────────────────────────────────────
        if self._is_today:
            bg, fg, strike, weight = t["today_bg"], t["today_text"], "none", "bold"
        elif self._is_past and self._this_month:
            bg, fg, strike, weight = (
                t["past_bg"],
                t["past_text"],
                "line-through",
                "normal",
            )
        elif not self._this_month:
            bg, fg, strike, weight = (
                "transparent",
                t["day_text_muted"],
                "none",
                "normal",
            )
        else:
            bg, fg, strike, weight = t["day_bg"], t["day_text"], "none", "normal"

        hover_bg = t["day_bg_hover"] if not self._is_today else t["today_bg"]
        radius = max(6, fs // 2)  # border-radius scales with font

        self.setStyleSheet(
            f"""
            DayCell {{
                background:    {bg};
                border:        none;
                border-radius: {radius}px;
            }}
            DayCell:hover {{
                background:    {hover_bg};
            }}
        """
        )

        # ── day number label ──────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl = QLabel(str(self._day))
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._lbl.setStyleSheet(
            f"""
            color:           {fg};
            font-size:       {fs}px;
            font-family:     '{TC.FONT_FAMILY}';
            font-weight:     {weight};
            text-decoration: {strike};
            background:      transparent;
        """
        )
        layout.addWidget(self._lbl)

        # ── task dot — top-right corner circle ───────────────────────────────
        if self._has_task and self._this_month and not self._is_past:
            dot_size = max(6, fs // 2)
            self._dot = QLabel(self)
            self._dot.setFixedSize(dot_size, dot_size)
            self._dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._dot.setStyleSheet(
                f"""
                background:    {t["dot_color"]};
                border-radius: {dot_size // 2}px;
            """
            )
            # Position is set in resizeEvent so it tracks the cell size
            self._dot.show()
        else:
            self._dot = None

    def resizeEvent(self, event):
        """Keep the dot pinned to the top-right corner as the cell resizes."""
        super().resizeEvent(event)
        if self._dot:
            margin = max(3, self._font_size // 5)
            self._dot.move(self.width() - self._dot.width() - margin, margin)


# ─────────────────────────────────────────────
# Main Calendar Widget
# ─────────────────────────────────────────────
class CalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = CalStorage.load_settings()
        self._today = date.today()
        self._year = self._today.year
        self._month = self._today.month
        self._due_dates = set()
        self._drag_pos = None
        self._rebuilding = False  # re-entrancy guard for _rebuild_grid

        self._setup_window()
        self._build_ui()
        self._setup_tray()
        self._setup_timers()
        self._refresh()

        if self.settings.get("startup", True):
            StartupManager.enable()

    # ── Window flags ────────────────────────────────────────────────────────
    def _setup_window(self):
        s = self.settings
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setGeometry(s["x"], s["y"], s["width"], s["height"])
        self.setMinimumSize(300, 300)
        self.setWindowOpacity(s.get("opacity", 0.92))

    # ── Build static UI skeleton ─────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName("card")
        self._card_layout = QVBoxLayout(self.card)
        self._card_layout.setContentsMargins(14, 12, 14, 10)
        self._card_layout.setSpacing(6)

        # ── Navigation header ────────────────────────────────────────────────
        nav = QHBoxLayout()
        nav.setSpacing(6)

        self._prev_btn = QPushButton("‹")
        self._prev_btn.setFixedSize(32, 32)
        self._prev_btn.setToolTip("Previous month")
        self._prev_btn.clicked.connect(self._go_prev)
        nav.addWidget(self._prev_btn)

        # Clickable month+year label → opens JumpDialog
        self._month_lbl = QPushButton("")
        self._month_lbl.setFlat(True)
        self._month_lbl.setToolTip("Click to jump to a month")
        self._month_lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._month_lbl.clicked.connect(self._jump_to_month)
        nav.addWidget(self._month_lbl, stretch=1)

        self._next_btn = QPushButton("›")
        self._next_btn.setFixedSize(32, 32)
        self._next_btn.setToolTip("Next month")
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._next_btn)

        self._today_btn = QPushButton("Today")
        self._today_btn.setFixedHeight(32)
        self._today_btn.setToolTip("Jump to today")
        self._today_btn.clicked.connect(self._go_today)
        nav.addWidget(self._today_btn)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setFlat(True)
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self._open_settings)
        nav.addWidget(self._settings_btn)

        self._card_layout.addLayout(nav)

        # ── Weekday headers — expand with the grid, no fixed width ─────────────
        self._weekday_row = QHBoxLayout()
        self._weekday_row.setSpacing(4)
        self._weekday_labels = []
        for d in DAYS_SHORT:
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self._weekday_labels.append(lbl)
            self._weekday_row.addWidget(lbl)
        self._card_layout.addLayout(self._weekday_row)

        # ── Day grid — expands to fill all available space ───────────────────
        self._grid_container = QWidget()
        self._grid_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(4)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        # All 7 columns equal width
        for col in range(7):
            self._grid_layout.setColumnStretch(col, 1)
        self._card_layout.addWidget(self._grid_container, stretch=1)

        # ── Bottom: resize grip ──────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.addStretch()
        grip = QSizeGrip(self.card)
        grip.setFixedSize(16, 16)
        bottom.addWidget(grip)
        self._card_layout.addLayout(bottom)

        outer.addWidget(self.card)

    # ── System tray ──────────────────────────────────────────────────────────
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_FileDialogDetailedView
            )
        )
        self.tray.setToolTip("Desktop Calendar")

        menu = QMenu()
        show = QAction("Show Calendar", self)
        show.triggered.connect(self.show)
        menu.addAction(show)

        today_act = QAction("Go to Today", self)
        today_act.triggered.connect(self._go_today)
        menu.addAction(today_act)

        menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self._exit_app)
        menu.addAction(exit_act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: (
                self.setVisible(not self.isVisible())
                if r == QSystemTrayIcon.ActivationReason.DoubleClick
                else None
            )
        )
        self.tray.show()

    # ── Timers ───────────────────────────────────────────────────────────────
    def _setup_timers(self):
        # Save position every 5s
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self._save_state)
        self._save_timer.start(5000)

        # Reload task dots + roll over midnight every 60s
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._tick)
        self._refresh_timer.start(60_000)

        # Debounce timer for resize — fires 80ms after the last resize event
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_resize_done)

    def _tick(self):
        new_today = date.today()
        if new_today != self._today:
            self._today = new_today  # midnight rollover
        self._due_dates = CalStorage.load_due_dates()
        self._rebuild_grid()

    # ── Full refresh (theme + grid) ──────────────────────────────────────────
    def _refresh(self):
        self._due_dates = CalStorage.load_due_dates()
        self._apply_theme()

    def _apply_theme(self):
        dark = self.settings.get("dark_mode", True)
        t = get_cal_theme(dark)
        self.setWindowOpacity(self.settings.get("opacity", 0.92))

        self.card.setStyleSheet(
            f"""
            QFrame#card {{
                background:    {t["card_bg"]};
                border:        1px solid {t["border"]};
                border-radius: {t["card_radius"]};
            }}
            QLabel {{
                color:      {t["text"]};
                background: transparent;
            }}
        """
        )

        # Nav buttons
        nav_style = f"""
            QPushButton {{
                background:    {t["nav_btn"]};
                color:         {t["text"]};
                border:        none;
                border-radius: 8px;
                font-size:     18px;
                font-family:   '{TC.FONT_FAMILY}';
                font-weight:   bold;
            }}
            QPushButton:hover {{ background: {t["nav_btn_hover"]}; }}
        """
        self._prev_btn.setStyleSheet(nav_style)
        self._next_btn.setStyleSheet(nav_style)

        # Month/year label (flat button)
        self._month_lbl.setStyleSheet(
            f"""
            QPushButton {{
                background:  transparent;
                color:       {t["text"]};
                border:      none;
                font-size:   17px;
                font-family: '{TC.FONT_FAMILY}';
                font-weight: bold;
                text-align:  left;
                padding-left: 4px;
            }}
            QPushButton:hover {{ color: {t["dot_color"]}; }}
        """
        )

        self._today_btn.setStyleSheet(
            f"""
            QPushButton {{
                background:    {t["today_btn_bg"]};
                color:         {t["today_bg"]};
                border:        none;
                border-radius: 8px;
                font-size:     12px;
                font-family:   '{TC.FONT_FAMILY}';
                font-weight:   bold;
                padding:       0 8px;
            }}
            QPushButton:hover {{ background: {t["today_btn_hover"]}; }}
        """
        )

        self._settings_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; color: {t["text_muted"]};
                border: none; font-size: 15px;
            }}
            QPushButton:hover {{ color: {t["text"]}; }}
        """
        )

        # Weekday labels
        for lbl in self._weekday_labels:
            lbl.setStyleSheet(
                f"""
                color:       {t["weekday_text"]};
                font-size:   11px;
                font-family: '{TC.FONT_FAMILY}';
                font-weight: bold;
            """
            )

        self._rebuild_grid()

    # ── Rebuild day grid ─────────────────────────────────────────────────────
    def _rebuild_grid(self):
        # Re-entrancy guard — resizeEvent fires during navigation; ignore those
        if self._rebuilding:
            return
        self._rebuilding = True
        try:
            self._do_rebuild_grid()
        finally:
            self._rebuilding = False

    def _do_rebuild_grid(self):
        # Remove old cells safely: reparent to None so Qt releases them
        # immediately rather than deferring via deleteLater (which can
        # cause use-after-free crashes when nav buttons re-trigger a rebuild)
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # immediate, safe removal
                w.hide()

        dark = self.settings.get("dark_mode", True)
        t = get_cal_theme(dark)

        # ── Compute font size from current widget width ───────────────────────
        # Grid is 7 columns; estimate cell width from total widget width.
        # Font is ~35% of cell width, clamped to a sensible range.
        cell_w = max(28, (self.width() - 28) // 7)  # 28px = left+right margins
        fs = max(10, min(26, int(cell_w * 0.35)))

        # Grid row spacing also scales slightly
        gap = max(2, cell_w // 12)
        self._grid_layout.setSpacing(gap)

        # Update weekday header font size too
        for lbl in self._weekday_labels:
            lbl.setStyleSheet(
                lbl.styleSheet().split("font-size")[0]
                + f"font-size: {max(9, fs - 3)}px; font-family: '{TC.FONT_FAMILY}'; font-weight: bold;"
            )

        cal = self._month_calendar_sunday_first(self._year, self._month)

        # Update month label
        month_name = date(self._year, self._month, 1).strftime("%B %Y")
        self._month_lbl.setText(f"  {month_name}")

        today = self._today

        for row_idx, week in enumerate(cal):
            self._grid_layout.setRowStretch(row_idx, 1)
            for col_idx, day in enumerate(week):
                if day == 0:
                    cell = DayCell(0, False, False, False, False, t, fs)
                else:
                    cell_date = date(self._year, self._month, day)
                    is_today = cell_date == today
                    is_past = cell_date < today
                    has_task = cell_date in self._due_dates
                    cell = DayCell(day, True, is_today, is_past, has_task, t, fs)
                self._grid_layout.addWidget(cell, row_idx, col_idx)

    @staticmethod
    def _month_calendar_sunday_first(year: int, month: int) -> list:
        """
        Returns a list of weeks (each a list of 7 ints, 0=no day).
        Week starts on Sunday. Uses calendar.Calendar(firstweekday=6)
        which is the correct way — no manual rotation needed.

        Col index: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
        """
        cal = calendar.Calendar(firstweekday=6)
        return cal.monthdayscalendar(year, month)

    # ── Navigation ───────────────────────────────────────────────────────────
    def _go_prev(self):
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._rebuild_grid()

    def _go_next(self):
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._rebuild_grid()

    def _go_today(self):
        self._today = date.today()
        self._year = self._today.year
        self._month = self._today.month
        self._rebuild_grid()

    def _jump_to_month(self):
        dlg = JumpDialog(
            self._year,
            self._month,
            dark=self.settings.get("dark_mode", True),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            y, m = dlg.get_result()
            self._year, self._month = y, m
            self._rebuild_grid()

    # ── Settings ─────────────────────────────────────────────────────────────
    def _open_settings(self):
        dlg = SettingsPanel(
            self.settings, dark=self.settings.get("dark_mode", True), parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()
            self.settings.update(result)
            if result["startup"]:
                StartupManager.enable()
            else:
                StartupManager.disable()
            CalStorage.save_settings(self.settings)
            self._apply_theme()

    # ── Persistence ──────────────────────────────────────────────────────────
    def _save_state(self):
        geo = self.geometry()
        self.settings.update(
            {
                "x": geo.x(),
                "y": geo.y(),
                "width": geo.width(),
                "height": geo.height(),
            }
        )
        CalStorage.save_settings(self.settings)

    # ── Tray / close ─────────────────────────────────────────────────────────
    def _exit_app(self):
        self._save_state()
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Desktop Calendar",
            "Minimized to tray. Double-click to restore.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    # ── Drag to move ─────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def resizeEvent(self, event):
        """Debounce resize so we only rebuild grid after user stops dragging."""
        super().resizeEvent(event)
        if hasattr(self, "_resize_timer"):
            self._resize_timer.start(80)  # restart 80ms countdown each pixel

    def _on_resize_done(self):
        if hasattr(self, "_grid_layout") and not self._rebuilding:
            self._rebuild_grid()

    def paintEvent(self, event):
        pass  # transparent outer window; card paints itself


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    widget = CalendarWidget()
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
