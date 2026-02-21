"""
Windows Desktop To-Do Widget  ·  v1.2
Stack : Python + PyQt6

All colors, fonts, and sizes live in theme_config.py — edit that file
to customise the look without touching anything here.

Changes in v1.2:
  - Removed list/category dropdown — all tasks shown together, no categories
  - Replaced the full add-task input bar with a single floating + button
    in the bottom-right corner; clicking it opens the add-task dialog
"""

import sys
import json
import os
import uuid
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QSystemTrayIcon,
    QMenu,
    QDialog,
    QDateTimeEdit,
    QComboBox,
    QSizeGrip,
    QSlider,
    QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QDateTime
from PyQt6.QtGui import QIcon, QFont, QAction, QCursor

# ── Pull everything visual from theme_config.py ──────────────────────────────
import theme_config as TC


# ─────────────────────────────────────────────
# Constants & Paths
# ─────────────────────────────────────────────
APP_NAME = "DesktopTodo"
DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / APP_NAME
DATA_FILE = DATA_DIR / "tasks.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────
class Task:
    def __init__(
        self,
        title: str,
        list_name: str = None,
        due: str = None,
        task_id: str = None,
        completed: bool = False,
        reminder_sent: bool = False,
    ):
        self.id = task_id or str(uuid.uuid4())
        self.title = title
        self.list_name = list_name or TC.DEFAULT_LIST_NAME
        self.due = due
        self.completed = completed
        self.reminder_sent = reminder_sent
        self.created = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "list_name": self.list_name,
            "due": self.due,
            "completed": self.completed,
            "reminder_sent": self.reminder_sent,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d):
        t = cls(
            title=d["title"],
            list_name=d.get("list_name", TC.DEFAULT_LIST_NAME),
            due=d.get("due"),
            task_id=d["id"],
            completed=d.get("completed", False),
            reminder_sent=d.get("reminder_sent", False),
        )
        t.created = d.get("created", datetime.now().isoformat())
        return t

    @property
    def is_overdue(self):
        if not self.due or self.completed:
            return False
        try:
            return datetime.fromisoformat(self.due) < datetime.now()
        except ValueError:
            return False


# ─────────────────────────────────────────────
# Storage Manager
# ─────────────────────────────────────────────
class StorageManager:
    _lock = threading.Lock()

    @staticmethod
    def load_tasks() -> list:
        if not DATA_FILE.exists():
            return []
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Task.from_dict(d) for d in data.get("tasks", [])]
        except (json.JSONDecodeError, KeyError):
            return []

    @staticmethod
    def save_tasks(tasks: list):
        with StorageManager._lock:
            tmp = DATA_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"tasks": [t.to_dict() for t in tasks]}, f, indent=2)
            tmp.replace(DATA_FILE)

    @staticmethod
    def load_settings() -> dict:
        defaults = {
            "x": TC.DEFAULT_X,
            "y": TC.DEFAULT_Y,
            "width": TC.DEFAULT_WIDTH,
            "height": TC.DEFAULT_HEIGHT,
            "dark_mode": TC.DEFAULT_DARK_MODE,
            "opacity": TC.DEFAULT_OPACITY,
            "font_size": TC.FONT_SIZE_DEFAULT,
            "active_list": TC.DEFAULT_LIST_NAME,
            "startup": TC.DEFAULT_STARTUP,
            "all_lists": [TC.DEFAULT_LIST_NAME],
        }
        if not SETTINGS_FILE.exists():
            return defaults
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            defaults.update(loaded)
            if TC.DEFAULT_LIST_NAME not in defaults["all_lists"]:
                defaults["all_lists"].insert(0, TC.DEFAULT_LIST_NAME)
            return defaults
        except (json.JSONDecodeError, KeyError):
            return defaults

    @staticmethod
    def save_settings(settings: dict):
        with StorageManager._lock:
            tmp = SETTINGS_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            tmp.replace(SETTINGS_FILE)


# ─────────────────────────────────────────────
# Startup Manager
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
                winreg.SetValueEx(key, StartupManager.APP_KEY, 0, winreg.REG_SZ, exe)
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
                winreg.DeleteValue(key, StartupManager.APP_KEY)
        except Exception:
            pass

    @staticmethod
    def is_enabled() -> bool:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, StartupManager.REG_KEY
            ) as key:
                winreg.QueryValueEx(key, StartupManager.APP_KEY)
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────
# Notification Manager
# ─────────────────────────────────────────────
class NotificationManager:
    @staticmethod
    def send(title: str, message: str):
        try:
            from winotify import Notification, audio

            toast = Notification(
                app_id=APP_NAME, title=title, msg=message, duration="short"
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
        except ImportError:
            pass

    @staticmethod
    def check_and_notify(tasks: list):
        now = datetime.now()
        for task in tasks:
            if task.completed or task.reminder_sent or not task.due:
                continue
            try:
                due_dt = datetime.fromisoformat(task.due)
                early = TC.REMINDER_EARLY_WARNING_SECONDS
                if now >= due_dt:
                    NotificationManager.send("Task Due", f'"{task.title}" is due now!')
                    task.reminder_sent = True
                elif (due_dt - now).total_seconds() <= early:
                    mins = int(early / 60)
                    NotificationManager.send(
                        "Task Due Soon", f'"{task.title}" is due in ~{mins} minutes.'
                    )
            except ValueError:
                pass


# ─────────────────────────────────────────────
# Task Item Widget
# ─────────────────────────────────────────────
class TaskItemWidget(QFrame):
    toggled = pyqtSignal(str)
    deleted = pyqtSignal(str)

    def __init__(self, task: Task, dark: bool, font_size: int, parent=None):
        super().__init__(parent)
        self.task = task
        self.dark = dark
        self.font_size = font_size
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.check = QCheckBox()
        self.check.setChecked(self.task.completed)
        self.check.toggled.connect(lambda _: self.toggled.emit(self.task.id))
        layout.addWidget(self.check)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)

        self.title_lbl = QLabel(self.task.title)
        self.title_lbl.setFont(QFont(TC.FONT_FAMILY, self.font_size))
        self.title_lbl.setWordWrap(True)
        text_col.addWidget(self.title_lbl)

        if self.task.due:
            try:
                dt = datetime.fromisoformat(self.task.due)
                due_str = dt.strftime("%b %d  %H:%M")
                theme = TC.get_theme(self.dark)
                color = (
                    theme["overdue_color"]
                    if self.task.is_overdue
                    else theme["due_color"]
                )
                self.due_lbl = QLabel(f"Due: {due_str}")
                fs_due = self.font_size + TC.FONT_SIZE_DUE_LABEL_OFFSET
                self.due_lbl.setFont(QFont(TC.FONT_FAMILY, max(fs_due, 8)))
                self.due_lbl.setStyleSheet(f"color: {color};")
                text_col.addWidget(self.due_lbl)
            except ValueError:
                pass

        layout.addLayout(text_col, stretch=1)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(TC.DELETE_BTN_SIZE, TC.DELETE_BTN_SIZE)
        del_btn.setFlat(True)
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.clicked.connect(lambda: self.deleted.emit(self.task.id))
        layout.addWidget(del_btn)

    def _apply_style(self):
        theme = TC.get_theme(self.dark)
        strike = "line-through" if self.task.completed else "none"
        alpha = "0.5" if self.task.completed else "1.0"
        self.setStyleSheet(
            f"""
            TaskItemWidget {{
                background:    {theme["task_bg"]};
                border:        1px solid {theme["task_border"]};
                border-radius: {theme["task_radius"]};
            }}
            QLabel {{
                color:           {theme["text"]};
                text-decoration: {strike};
                opacity:         {alpha};
                background:      transparent;
            }}
            QPushButton:flat       {{ background: transparent; color: {theme["text_muted"]}; }}
            QPushButton:flat:hover {{ color: #ff5555; }}
        """
        )


# ─────────────────────────────────────────────
# Add / Edit Task Dialog  (no list field)
# ─────────────────────────────────────────────
class TaskDialog(QDialog):
    def __init__(self, task: Task = None, dark: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Task" if task else "New Task")
        self.setFixedWidth(320)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self._build_ui(task)
        self._apply_style(dark)

    def _build_ui(self, task):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("What needs to be done?")
        self.title_input.returnPressed.connect(self.accept)
        if task:
            self.title_input.setText(task.title)
        layout.addWidget(self.title_input)

        self.has_due = QCheckBox("Set due date / time")
        self.has_due.setChecked(bool(task and task.due))
        layout.addWidget(self.has_due)

        self.due_dt = QDateTimeEdit()
        self.due_dt.setCalendarPopup(True)
        self.due_dt.setDisplayFormat("MMM dd yyyy  HH:mm")
        if task and task.due:
            try:
                dt = datetime.fromisoformat(task.due)
                self.due_dt.setDateTime(
                    QDateTime.fromString(
                        dt.strftime("%Y-%m-%d %H:%M"), "yyyy-MM-dd HH:mm"
                    )
                )
            except ValueError:
                self.due_dt.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        else:
            self.due_dt.setDateTime(QDateTime.currentDateTime().addSecs(3600))

        self.due_dt.setEnabled(self.has_due.isChecked())
        self.has_due.toggled.connect(self.due_dt.setEnabled)
        layout.addWidget(self.due_dt)

        btns = QHBoxLayout()
        ok_btn = QPushButton("Add" if not task else "Save")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _apply_style(self, dark: bool):
        t = TC.get_dialog_theme(dark)
        self.setStyleSheet(
            f"""
            QDialog {{ background: {t["bg"]}; color: {t["text"]}; }}
            QLabel, QCheckBox {{ color: {t["text"]}; background: transparent; }}
            QLineEdit, QDateTimeEdit {{
                background: {t["input_bg"]}; color: {t["text"]};
                border: 1px solid {t["border"]}; border-radius: 6px; padding: 6px;
            }}
            QPushButton {{
                background: {t["btn_bg"]}; color: white;
                border-radius: 6px; padding: 8px 18px; border: none;
            }}
            QPushButton:hover {{ background: {t["btn_hover"]}; }}
        """
        )

    def get_result(self):
        title = self.title_input.text().strip()
        due = None
        if self.has_due.isChecked():
            due = self.due_dt.dateTime().toPyDateTime().isoformat()
        return title, due


# ─────────────────────────────────────────────
# Settings Panel
# ─────────────────────────────────────────────
class SettingsPanel(QDialog):
    def __init__(self, settings: dict, dark: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Widget Settings")
        self.setFixedWidth(300)
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
        layout.setSpacing(14)

        layout.addWidget(QLabel("Opacity:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(
            int(settings.get("opacity", TC.DEFAULT_OPACITY) * 100)
        )
        layout.addWidget(self.opacity_slider)

        layout.addWidget(QLabel("Font Size:"))
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(9, 20)
        self.font_slider.setValue(settings.get("font_size", TC.FONT_SIZE_DEFAULT))
        layout.addWidget(self.font_slider)

        self.dark_check = QCheckBox("Dark Mode")
        self.dark_check.setChecked(settings.get("dark_mode", TC.DEFAULT_DARK_MODE))
        layout.addWidget(self.dark_check)

        self.startup_check = QCheckBox("Launch at Windows startup")
        self.startup_check.setChecked(StartupManager.is_enabled())
        layout.addWidget(self.startup_check)

        ok_btn = QPushButton("Apply & Close")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

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
            "opacity": self.opacity_slider.value() / 100,
            "font_size": self.font_slider.value(),
            "dark_mode": self.dark_check.isChecked(),
            "startup": self.startup_check.isChecked(),
        }


# ─────────────────────────────────────────────
# Main Widget Window
# ─────────────────────────────────────────────
class DesktopWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = StorageManager.load_settings()
        self.tasks = StorageManager.load_tasks()
        self._drag_pos = None

        self._setup_window()
        self._build_ui()
        self._setup_tray()
        self._apply_theme()
        self._setup_timers()

        if self.settings.get("startup", TC.DEFAULT_STARTUP):
            StartupManager.enable()

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
        self.setMinimumSize(TC.MIN_WIDTH, TC.MIN_HEIGHT)
        self.setWindowOpacity(s.get("opacity", TC.DEFAULT_OPACITY))

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        # ── Header ──────────────────────────────
        header = QHBoxLayout()
        self.title_lbl = QLabel("✓ To-Do")
        header.addWidget(self.title_lbl)
        header.addStretch()

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(TC.SETTINGS_BTN_SIZE, TC.SETTINGS_BTN_SIZE)
        settings_btn.setFlat(True)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(settings_btn)
        card_layout.addLayout(header)

        # ── Task scroll area ─────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.task_layout.setSpacing(4)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.task_container)
        card_layout.addWidget(scroll, stretch=1)

        # ── Bottom bar: resize grip + FAB ────────
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)

        grip = QSizeGrip(self.card)
        grip.setFixedSize(16, 16)
        bottom.addWidget(grip)

        bottom.addStretch()

        # Floating Action Button — the ONLY way to add a task
        self.fab = QPushButton("+")
        self.fab.setFixedSize(36, 36)
        self.fab.setToolTip("Add a task")
        self.fab.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.fab.setObjectName("fab")
        self.fab.clicked.connect(self._open_add_dialog)
        bottom.addWidget(self.fab)

        card_layout.addLayout(bottom)
        outer.addWidget(self.card)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_DialogApplyButton
            )
        )
        self.tray.setToolTip("Desktop To-Do")

        menu = QMenu()
        show_act = QAction("Show Widget", self)
        show_act.triggered.connect(self.show)
        menu.addAction(show_act)

        add_act = QAction("Quick Add Task", self)
        add_act.triggered.connect(self._quick_add_from_tray)
        menu.addAction(add_act)

        menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self._exit_app)
        menu.addAction(exit_act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _setup_timers(self):
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self._save_state)
        self._save_timer.start(TC.SAVE_INTERVAL_MS)

        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._check_reminders)
        self._notif_timer.start(TC.REMINDER_INTERVAL_MS)

    # ══════════════════════════════════════════
    #  THEME
    # ══════════════════════════════════════════

    def _apply_theme(self):
        dark = self.settings.get("dark_mode", TC.DEFAULT_DARK_MODE)
        fs = self.settings.get("font_size", TC.FONT_SIZE_DEFAULT)
        theme = TC.get_theme(dark)
        self.setWindowOpacity(self.settings.get("opacity", TC.DEFAULT_OPACITY))

        flat_hover = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.06)"

        self.card.setStyleSheet(
            f"""
            QFrame#card {{
                background:    {theme["card_bg"]};
                border:        1px solid {theme["border"]};
                border-radius: {theme["card_radius"]};
            }}
            QLabel {{ color: {theme["text"]}; background: transparent; }}
            QLineEdit, QComboBox {{
                background:    {theme["input_bg"]};
                color:         {theme["text"]};
                border:        1px solid {theme["border"]};
                border-radius: {theme["input_radius"]};
                padding:       5px 8px;
                font-size:     {fs}px;
                font-family:   '{TC.FONT_FAMILY}';
            }}
            QPushButton {{
                background:    {theme["btn_bg"]};
                color:         white;
                border:        none;
                border-radius: {theme["btn_radius"]};
                font-size:     {fs}px;
                font-family:   '{TC.FONT_FAMILY}';
            }}
            QPushButton:hover {{ background: {theme["btn_hover"]}; }}
            QPushButton:flat  {{ background: transparent; color: {theme["text"]}; }}
            QPushButton:flat:hover {{ background: {flat_hover}; }}
            QScrollArea {{ background: {theme["scroll_bg"]}; border: none; }}
            QScrollBar:vertical {{
                background: {theme["scroll_track"]}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme["scroll_thumb"]}; border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """
        )

        self.title_lbl.setFont(QFont(TC.FONT_FAMILY, fs + 1, QFont.Weight.Bold))

        # Style the FAB separately so it's always a solid circle, not flat
        self.fab.setStyleSheet(
            f"""
            QPushButton#fab {{
                background:    {theme["btn_bg"]};
                color:         white;
                border:        none;
                border-radius: 18px;
                font-size:     22px;
                font-weight:   bold;
            }}
            QPushButton#fab:hover {{ background: {theme["btn_hover"]}; }}
        """
        )

        self._populate_tasks()

    # ══════════════════════════════════════════
    #  TASK RENDERING
    # ══════════════════════════════════════════

    def _populate_tasks(self):
        while self.task_layout.count():
            item = self.task_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        dark = self.settings.get("dark_mode", TC.DEFAULT_DARK_MODE)
        fs = self.settings.get("font_size", TC.FONT_SIZE_DEFAULT)
        theme = TC.get_theme(dark)

        # All tasks — no list filtering
        pending = sorted(
            [t for t in self.tasks if not t.completed],
            key=lambda t: (not t.is_overdue, t.due or "9999"),
        )
        done = [t for t in self.tasks if t.completed]

        for task in pending + done:
            row = TaskItemWidget(task, dark, fs)
            row.toggled.connect(self._toggle_task)
            row.deleted.connect(self._delete_task)
            self.task_layout.addWidget(row)

        if not self.tasks:
            lbl = QLabel("Nothing to do — hit + to add a task!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {theme['text_muted']}; padding: 20px;")
            self.task_layout.addWidget(lbl)

    # ══════════════════════════════════════════
    #  TASK CRUD
    # ══════════════════════════════════════════

    def _open_add_dialog(self):
        """FAB click — open the add task dialog."""
        dlg = TaskDialog(
            dark=self.settings.get("dark_mode", TC.DEFAULT_DARK_MODE), parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        title, due = dlg.get_result()
        if not title:
            return
        self.tasks.append(Task(title=title, due=due))
        StorageManager.save_tasks(self.tasks)
        self._populate_tasks()

    def _toggle_task(self, task_id: str):
        for t in self.tasks:
            if t.id == task_id:
                t.completed = not t.completed
                if not t.completed:
                    t.reminder_sent = False
                break
        StorageManager.save_tasks(self.tasks)
        self._populate_tasks()

    def _delete_task(self, task_id: str):
        self.tasks = [t for t in self.tasks if t.id != task_id]
        StorageManager.save_tasks(self.tasks)
        self._populate_tasks()

    def _open_settings(self):
        dlg = SettingsPanel(
            self.settings,
            dark=self.settings.get("dark_mode", TC.DEFAULT_DARK_MODE),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()
            self.settings.update(result)
            if result["startup"]:
                StartupManager.enable()
            else:
                StartupManager.disable()
            StorageManager.save_settings(self.settings)
            self._apply_theme()

    def _check_reminders(self):
        NotificationManager.check_and_notify(self.tasks)
        StorageManager.save_tasks(self.tasks)

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
        StorageManager.save_settings(self.settings)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.setVisible(not self.isVisible())

    def _quick_add_from_tray(self):
        self.show()
        self.raise_()
        self._open_add_dialog()

    def _exit_app(self):
        self._save_state()
        self.tray.hide()
        QApplication.quit()

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

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Desktop To-Do",
            "Widget minimized to tray. Double-click to restore.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def paintEvent(self, event):
        pass


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    widget = DesktopWidget()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
