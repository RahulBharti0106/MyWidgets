from datetime import datetime

from PyQt6.QtCore import QDate, QDateTime, QTime, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QAbstractSpinBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from todo import todo_theme as TC


class AddTaskModal(QDialog):
    CATEGORY_OPTIONS = [
        ("general", "General"),
        ("work", "Work"),
        ("study", "Study"),
        ("personal", "Personal"),
    ]

    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self._category = "general"
        self._is_important = False
        self._category_buttons = {}
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
        self._apply_style()
        self._sync_category_buttons()
        self._sync_ok_state()

    def _build_ui(self, task):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("What needs to be done?")
        self.title_input.returnPressed.connect(self.accept)
        self.title_input.textChanged.connect(self._sync_ok_state)
        if task:
            self.title_input.setText(task.title)
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Category"))

        category_wrap = QWidget()
        category_layout = QVBoxLayout(category_wrap)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(8)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        for value, label in self.CATEGORY_OPTIONS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.clicked.connect(
                lambda checked=False, selected=value: self._set_category(selected)
            )
            row.addWidget(btn, stretch=1)
            self._category_buttons[value] = btn
        category_layout.addLayout(row)

        self.important_btn = QPushButton("Important ★")
        self.important_btn.setCheckable(True)
        self.important_btn.setFixedHeight(28)
        self.important_btn.clicked.connect(self._toggle_important)
        category_layout.addWidget(self.important_btn)

        if task:
            self._category = getattr(task, "category", "general")
            self._is_important = getattr(task, "is_important", False)
        self.important_btn.setChecked(self._is_important)

        layout.addWidget(category_wrap)

        self.has_due = QCheckBox("Set due date / time")
        self.has_due.setChecked(bool(task and task.due))
        layout.addWidget(self.has_due)

        self.due_controls = QWidget()
        due_controls_layout = QVBoxLayout(self.due_controls)
        due_controls_layout.setContentsMargins(0, 0, 0, 0)
        due_controls_layout.setSpacing(6)

        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(6)

        today_btn = QPushButton("Today")
        today_btn.setFixedHeight(28)
        today_btn.clicked.connect(lambda: self._set_due_preset(0))
        preset_row.addWidget(today_btn, stretch=1)

        tomorrow_btn = QPushButton("Tomorrow")
        tomorrow_btn.setFixedHeight(28)
        tomorrow_btn.clicked.connect(lambda: self._set_due_preset(1))
        preset_row.addWidget(tomorrow_btn, stretch=1)

        due_controls_layout.addLayout(preset_row)

        manual_row = QHBoxLayout()
        manual_row.setContentsMargins(0, 0, 0, 0)
        manual_row.setSpacing(6)

        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        self.due_date.setDisplayFormat("MMM dd yyyy")
        manual_row.addWidget(self.due_date, stretch=1)

        self.due_time = QTimeEdit()
        self.due_time.setDisplayFormat("HH:mm")
        self.due_time.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        manual_row.addWidget(self.due_time, stretch=1)

        due_controls_layout.addLayout(manual_row)

        if task and task.due:
            try:
                dt = datetime.fromisoformat(task.due)
                self.due_date.setDate(QDate(dt.year, dt.month, dt.day))
                self.due_time.setTime(QTime(dt.hour, dt.minute))
            except ValueError:
                fallback = QDateTime.currentDateTime().addSecs(3600)
                self.due_date.setDate(fallback.date())
                self.due_time.setTime(fallback.time())
        else:
            fallback = QDateTime.currentDateTime().addSecs(3600)
            self.due_date.setDate(fallback.date())
            self.due_time.setTime(fallback.time())

        self.due_controls.setVisible(self.has_due.isChecked())
        self.has_due.toggled.connect(self.due_controls.setVisible)
        layout.addWidget(self.due_controls)

        btns = QHBoxLayout()
        self.ok_btn = QPushButton("Add" if not task else "Save")
        self.ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _set_category(self, category: str):
        self._category = category
        self._sync_category_buttons()

    def _toggle_important(self, checked: bool):
        self._is_important = checked
        self._sync_category_buttons()

    def _sync_ok_state(self):
        self.ok_btn.setEnabled(bool(self.title_input.text().strip()))

    def _set_due_preset(self, days_ahead: int):
        now = QDateTime.currentDateTime()
        preset = now.addDays(days_ahead)
        preset.setTime(QTime(23, 59))
        self.has_due.setChecked(True)
        self.due_date.setDate(preset.date())
        self.due_time.setTime(preset.time())

    def _sync_category_buttons(self):
        for value, btn in self._category_buttons.items():
            btn.setChecked(value == self._category)
        self.important_btn.setChecked(self._is_important)
        self._apply_style()

    def _apply_style(self):
        t = TC.get_dialog_theme(True)
        widget_theme = TC.get_theme(True)
        inactive = (
            "background: {bg}; color: {text}; border: 1px solid {border}; "
            "border-radius: 6px; padding: 4px 8px;"
        ).format(
            bg=widget_theme["task_bg"],
            text=t["text"],
            border=widget_theme["task_border"],
        )
        active = (
            "background: {bg}; color: white; border: none; "
            "border-radius: 6px; padding: 4px 8px;"
        ).format(bg=widget_theme["btn_bg"])

        self.setStyleSheet(f"""
            QDialog {{ background: {t["bg"]}; color: {t["text"]}; }}
            QLabel, QCheckBox {{ color: {t["text"]}; background: transparent; }}
            QLineEdit, QDateEdit, QTimeEdit {{
                background: {t["input_bg"]}; color: {t["text"]};
                border: 1px solid {t["border"]}; border-radius: 6px; padding: 6px;
            }}
            QPushButton {{
                background: {t["btn_bg"]}; color: white;
                border-radius: 6px; padding: 8px 18px; border: none;
            }}
            QPushButton:hover {{ background: {t["btn_hover"]}; }}
        """)

        for value, btn in self._category_buttons.items():
            btn.setStyleSheet(active if value == self._category else inactive)
        self.important_btn.setStyleSheet(active if self._is_important else inactive)

    def get_result(self) -> tuple:
        title = self.title_input.text().strip()
        due = None
        if self.has_due.isChecked():
            due = (
                QDateTime(
                    self.due_date.date(),
                    self.due_time.time(),
                )
                .toPyDateTime()
                .isoformat()
            )
        return title, due, self._category, self._is_important
