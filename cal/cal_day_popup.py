import json
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from cal import cal_theme as TC

TODO_TASKS = Path(os.getenv("APPDATA", Path.home())) / "DesktopTodo" / "tasks.json"


class DayTaskPopup(QFrame):
    def __init__(self, target_date, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.target_date = target_date
        self.setObjectName("dayTaskPopup")
        self.setMinimumWidth(180)
        self.setMaximumWidth(240)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel(self.target_date.strftime("%a, %b %d"))
        header.setStyleSheet(
            f"color: {TC.CAL_DARK['text']}; font: 700 12px '{TC.FONT_FAMILY}';"
        )
        layout.addWidget(header)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(255,255,255,0.05); border: none;")
        layout.addWidget(divider)

        tasks = self._load_tasks_for_date()
        if not tasks:
            empty = QLabel("No tasks due")
            empty.setStyleSheet(f"color: {TC.CAL_DARK['text_muted']};")
            layout.addWidget(empty)
            return

        metrics = QFontMetrics(self.font())
        visible = tasks[:5]
        for task in visible:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            overdue = False
            try:
                overdue = datetime.fromisoformat(task["due"]) < datetime.now()
            except ValueError:
                pass

            dot = QLabel("\u25cf")
            dot_color = (
                TC.CAL_DARK["overdue_color"] if overdue else TC.CAL_DARK["dot_color"]
            )
            dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")
            row_layout.addWidget(dot, alignment=Qt.AlignmentFlag.AlignTop)

            title = QLabel(
                metrics.elidedText(task["title"], Qt.TextElideMode.ElideRight, 190)
            )
            title_color = TC.CAL_DARK["text_muted"] if overdue else TC.CAL_DARK["text"]
            title.setStyleSheet(
                f"color: {title_color}; font: 11px '{TC.FONT_FAMILY}'; background: transparent;"
            )
            row_layout.addWidget(title, stretch=1)
            layout.addWidget(row)

        if len(tasks) > 5:
            more = QLabel(f"+ {len(tasks) - 5} more")
            more.setStyleSheet(f"color: {TC.CAL_DARK['text_muted']};")
            layout.addWidget(more)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#dayTaskPopup {{
                background: {TC.CAL_DARK["card_bg"]};
                border: 1px solid {TC.CAL_DARK["border"]};
                border-radius: 10px;
            }}
            QLabel {{
                background: transparent;
                color: {TC.CAL_DARK["text"]};
            }}
        """)

    def _load_tasks_for_date(self):
        if not TODO_TASKS.exists():
            return []
        try:
            with open(TODO_TASKS, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        result = []
        for task in data.get("tasks", []):
            if task.get("completed", False) or not task.get("due"):
                continue
            try:
                due_date = datetime.fromisoformat(task["due"]).date()
            except ValueError:
                continue
            if due_date == self.target_date:
                result.append(task)
        return result
