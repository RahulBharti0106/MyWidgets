import sys
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sysconfig

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from calendar.cal_data import APP_NAME, CalStorage
from calendar.cal_day_popup import DayTaskPopup
from calendar.cal_theme import get_dialog_theme
from calendar.cal_ui import CalUI
from shared.startup_manager import StartupManager


def _load_stdlib_calendar():
    stdlib_dir = Path(sysconfig.get_paths()["stdlib"])
    calendar_py = stdlib_dir / "calendar.py"
    spec = spec_from_file_location("_stdlib_calendar", calendar_py)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_calendar = _load_stdlib_calendar()


class JumpDialog(QDialog):
    def __init__(self, current_year: int, current_month: int, parent=None):
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
        self._style()

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

    def _style(self):
        t = get_dialog_theme(True)
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


class SettingsPanel(QDialog):
    def __init__(self, settings: dict, parent=None):
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
        self._build_ui(settings)

    def _build_ui(self, settings):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel("Opacity:"))
        self.opacity_sl = QSlider(Qt.Orientation.Horizontal)
        self.opacity_sl.setRange(30, 100)
        self.opacity_sl.setValue(int(settings.get("opacity", 0.92) * 100))
        layout.addWidget(self.opacity_sl)

        from PyQt6.QtWidgets import QCheckBox

        self.startup_chk = QCheckBox("Launch at Windows startup")
        self.startup_chk.setChecked(StartupManager.is_enabled(APP_NAME))
        layout.addWidget(self.startup_chk)

        ok = QPushButton("Apply & Close")
        ok.clicked.connect(self.accept)
        layout.addWidget(ok)

        t = get_dialog_theme(True)
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
            "startup": self.startup_chk.isChecked(),
        }


class CalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = CalStorage.load_settings()
        self._today = date.today()
        self._year = self._today.year
        self._month = self._today.month
        self._task_counts = {}
        self._drag_pos = None
        self._rebuilding = False
        self._day_popup = None

        self._setup_window()
        self.ui = CalUI(self)
        self._setup_tray()
        self._setup_timers()
        self._refresh()

        if self.settings.get("startup", True):
            StartupManager.enable(APP_NAME)

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

    def _setup_timers(self):
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self._save_state)
        self._save_timer.start(5000)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._tick)
        self._refresh_timer.start(60_000)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_resize_done)

    def _tick(self):
        new_today = date.today()
        if new_today != self._today:
            self._today = new_today
        self._task_counts = CalStorage.load_task_counts()
        self._rebuild_grid()

    def _refresh(self):
        self._task_counts = CalStorage.load_task_counts()
        self._apply_theme()

    def _apply_theme(self):
        self.ui.apply_theme(self.settings)
        self._rebuild_grid()

    def _rebuild_grid(self):
        if self._rebuilding:
            return
        self._rebuilding = True
        try:
            self.ui.rebuild_grid(
                self._year, self._month, self._today, self._task_counts
            )
        finally:
            self._rebuilding = False

    @staticmethod
    def _month_calendar_sunday_first(year: int, month: int) -> list:
        cal = _calendar.Calendar(firstweekday=6)
        return cal.monthdayscalendar(year, month)

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
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            y, m = dlg.get_result()
            self._year, self._month = y, m
            self._rebuild_grid()

    def _open_settings(self):
        dlg = SettingsPanel(self.settings, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()
            self.settings.update(result)
            if result["startup"]:
                StartupManager.enable(APP_NAME)
            else:
                StartupManager.disable(APP_NAME)
            CalStorage.save_settings(self.settings)
            self._apply_theme()

    def _open_day_popup(self, target_date, badge_btn):
        if self._day_popup:
            self._day_popup.close()
        self._day_popup = DayTaskPopup(target_date, self)
        global_pos = badge_btn.mapToGlobal(QPoint(badge_btn.width(), 0))
        popup_size = self._day_popup.sizeHint()
        screen = self.screen().availableGeometry() if self.screen() else self.geometry()
        x = global_pos.x()
        y = global_pos.y()
        if x + popup_size.width() > screen.right():
            x = badge_btn.mapToGlobal(QPoint(-popup_size.width(), 0)).x()
        if y + popup_size.height() > screen.bottom():
            y = badge_btn.mapToGlobal(QPoint(0, -popup_size.height())).y()
        self._day_popup.move(QPoint(x, y))
        self._day_popup.show()
        self._day_popup.setFocus()

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
        super().resizeEvent(event)
        if hasattr(self, "_resize_timer"):
            self._resize_timer.start(80)

    def _on_resize_done(self):
        if hasattr(self, "_grid_layout") and not self._rebuilding:
            self._rebuild_grid()

    def paintEvent(self, event):
        pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    widget = CalendarWidget()
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
