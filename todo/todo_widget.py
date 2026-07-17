import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from shared.startup_manager import StartupManager
from todo import todo_theme as TC
from todo.todo_data import APP_NAME, StorageManager, Task
from todo.todo_logic import NotificationManager, filter_tasks
from todo.todo_modal import AddTaskModal
from todo.todo_sync import SyncManager
from todo.todo_ui import TodoUI


class SettingsPanel(QDialog):
    def __init__(self, settings: dict, parent=None):
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
        self._build_ui(settings)

    def _build_ui(self, settings):
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

        from PyQt6.QtWidgets import QCheckBox

        self.startup_check = QCheckBox("Launch at Windows startup")
        self.startup_check.setChecked(StartupManager.is_enabled(APP_NAME))
        layout.addWidget(self.startup_check)

        ok_btn = QPushButton("Apply & Close")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

        t = TC.get_dialog_theme(True)
        self.setStyleSheet(f"""
            QDialog {{ background: {t["bg"]}; color: {t["text"]}; }}
            QLabel, QCheckBox {{ color: {t["text"]}; background: transparent; }}
            QPushButton {{
                background: {t["btn_bg"]}; color: white;
                border-radius: 6px; padding: 8px; border: none;
            }}
            QPushButton:hover {{ background: {t["btn_hover"]}; }}
        """)

    def get_result(self):
        return {
            "opacity": self.opacity_slider.value() / 100,
            "font_size": self.font_slider.value(),
            "startup": self.startup_check.isChecked(),
        }


class DesktopTodoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = StorageManager.load_settings()
        self.tasks = StorageManager.load_tasks()
        self._drag_pos = None

        self._setup_window()
        self.ui = TodoUI(self)
        self._setup_tray()
        self._apply_theme()
        self._setup_timers()
        self._setup_sync()

        if self.settings.get("startup", TC.DEFAULT_STARTUP):
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
        self.setMinimumSize(TC.MIN_WIDTH, TC.MIN_HEIGHT)
        self.setWindowOpacity(s.get("opacity", TC.DEFAULT_OPACITY))

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

    def _setup_sync(self):
        self.sync_manager = SyncManager(self)
        self.sync_manager.tasks_updated.connect(self._reload_tasks_from_disk)
        self.sync_manager.new_tasks_arrived.connect(self._notify_new_tasks)
        self.sync_manager.start()

    def _current_category(self) -> str:
        return self.category_filter.currentData() or "all"

    def _apply_theme(self):
        self.ui.apply_theme(self.settings)
        self._populate_tasks()

    def _populate_tasks(self):
        dark = True
        fs = self.settings.get("font_size", TC.FONT_SIZE_DEFAULT)
        filtered = filter_tasks(self.tasks, self._current_category())
        self.ui.populate_tasks(filtered, dark, fs)

    def _on_category_changed(self):
        self._populate_tasks()

    def _open_add_dialog(self):
        dlg = AddTaskModal(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        title, due, category, is_important = dlg.get_result()
        if not title:
            return
        self.tasks.append(
            Task(
                title=title,
                due=due,
                category=category,
                is_important=is_important,
            )
        )
        SyncManager.save_local_tasks(self.tasks, dirty_ids={self.tasks[-1].id})
        self._populate_tasks()

    def _toggle_task(self, task_id: str):
        for t in self.tasks:
            if t.id == task_id:
                t.completed = not t.completed
                if not t.completed:
                    t.reminder_sent = False
                break
        SyncManager.save_local_tasks(self.tasks, dirty_ids={task_id})
        self._populate_tasks()

    def _delete_task(self, task_id: str):
        self.tasks = [t for t in self.tasks if t.id != task_id]
        SyncManager.queue_delete(task_id)
        SyncManager.save_local_tasks(self.tasks)
        self._populate_tasks()

    def _toggle_task_importance(self, task_id: str):
        for t in self.tasks:
            if t.id == task_id:
                t.is_important = not t.is_important
                break
        SyncManager.save_local_tasks(self.tasks, dirty_ids={task_id})
        self._populate_tasks()

    def _open_settings(self):
        dlg = SettingsPanel(self.settings, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.get_result()
            self.settings.update(result)
            if result["startup"]:
                StartupManager.enable(APP_NAME)
            else:
                StartupManager.disable(APP_NAME)
            StorageManager.save_settings(self.settings)
            self._apply_theme()

    def _check_reminders(self):
        before = {task.id: task.reminder_sent for task in self.tasks}
        NotificationManager.check_and_notify(self.tasks)
        dirty_ids = {
            task.id
            for task in self.tasks
            if task.reminder_sent != before.get(task.id, task.reminder_sent)
        }
        SyncManager.save_local_tasks(self.tasks, dirty_ids=dirty_ids)

    def _reload_tasks_from_disk(self):
        self.tasks = StorageManager.load_tasks()
        self._populate_tasks()

    def _notify_new_tasks(self, tasks: list):
        if not tasks:
            return
        if len(tasks) == 1:
            message = f"New task added: {tasks[0]['title']}"
        else:
            preview = ", ".join(task["title"] for task in tasks[:3])
            message = f"{len(tasks)} new tasks added while you were away"
            if preview:
                message = f"{message}: {preview}"
        self.tray.showMessage(
            "Desktop To-Do",
            message,
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

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
        if hasattr(self, "sync_manager"):
            self.sync_manager.stop()
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


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    widget = DesktopTodoWidget()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
