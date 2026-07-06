from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from todo import todo_theme as TC


class TaskItemWidget(QFrame):
    toggled = pyqtSignal(str)
    deleted = pyqtSignal(str)
    important_toggled = pyqtSignal(str)

    def __init__(self, task, dark: bool, font_size: int, parent=None):
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

        title = self.task.title
        if getattr(self.task, "is_important", False):
            title = f"★ {title}"
        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(QFont(TC.FONT_FAMILY, self.font_size))
        self.title_lbl.setWordWrap(True)
        text_col.addWidget(self.title_lbl)

        meta_parts = []
        category = getattr(self.task, "category", "general")
        if category:
            meta_parts.append(category.capitalize())

        if self.task.due:
            try:
                dt = datetime.fromisoformat(self.task.due)
                meta_parts.append(f"Due: {dt.strftime('%b %d  %H:%M')}")
            except ValueError:
                pass

        if meta_parts:
            theme = TC.get_theme(self.dark)
            color = (
                theme["overdue_color"]
                if self.task.is_overdue and self.task.due
                else theme["due_color"]
            )
            self.due_lbl = QLabel("  ".join(meta_parts))
            fs_due = self.font_size + TC.FONT_SIZE_DUE_LABEL_OFFSET
            self.due_lbl.setFont(QFont(TC.FONT_FAMILY, max(fs_due, 8)))
            self.due_lbl.setStyleSheet(f"color: {color};")
            text_col.addWidget(self.due_lbl)

        layout.addLayout(text_col, stretch=1)

        self.important_btn = QPushButton("★")
        self.important_btn.setCheckable(True)
        self.important_btn.setChecked(getattr(self.task, "is_important", False))
        self.important_btn.setFixedSize(TC.DELETE_BTN_SIZE, TC.DELETE_BTN_SIZE)
        self.important_btn.setFlat(True)
        self.important_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.important_btn.setToolTip("Mark important")
        self.important_btn.clicked.connect(
            lambda: self.important_toggled.emit(self.task.id)
        )
        layout.addWidget(self.important_btn)

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
        self.important_btn.setStyleSheet(
            f"color: {theme['btn_bg'] if self.task.is_important else theme['text_muted']};"
        )


class TodoUI:
    CATEGORY_OPTIONS = [
        ("All", "all"),
        ("Important ★", "important"),
        ("General", "general"),
        ("Work", "work"),
        ("Study", "study"),
        ("Personal", "personal"),
    ]

    def __init__(self, parent):
        self.parent = parent
        self._build_ui(parent)

    def _build_ui(self, parent):
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(0, 0, 0, 0)

        parent.card = QFrame(parent)
        parent.card.setObjectName("card")
        card_layout = QVBoxLayout(parent.card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        header = QHBoxLayout()
        parent.title_lbl = QLabel("✓ To-Do")
        header.addWidget(parent.title_lbl)
        header.addStretch()

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(TC.SETTINGS_BTN_SIZE, TC.SETTINGS_BTN_SIZE)
        settings_btn.setFlat(True)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(parent._open_settings)
        parent.settings_btn = settings_btn
        header.addWidget(settings_btn)
        card_layout.addLayout(header)

        parent.category_filter = QComboBox()
        for label, value in self.CATEGORY_OPTIONS:
            parent.category_filter.addItem(label, value)
        parent.category_filter.currentIndexChanged.connect(parent._on_category_changed)
        card_layout.addWidget(parent.category_filter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        parent.task_scroll = scroll

        parent.task_container = QWidget()
        parent.task_layout = QVBoxLayout(parent.task_container)
        parent.task_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        parent.task_layout.setSpacing(4)
        parent.task_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(parent.task_container)
        card_layout.addWidget(scroll, stretch=1)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)

        grip = QSizeGrip(parent.card)
        grip.setFixedSize(16, 16)
        bottom.addWidget(grip)

        bottom.addStretch()

        parent.fab = QPushButton("+")
        parent.fab.setFixedSize(36, 36)
        parent.fab.setToolTip("Add a task")
        parent.fab.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        parent.fab.setObjectName("fab")
        parent.fab.clicked.connect(parent._open_add_dialog)
        bottom.addWidget(parent.fab)

        card_layout.addLayout(bottom)
        outer.addWidget(parent.card)

    def apply_theme(self, settings):
        dark = True
        fs = settings.get("font_size", TC.FONT_SIZE_DEFAULT)
        theme = TC.get_theme(dark)
        self.parent.setWindowOpacity(settings.get("opacity", TC.DEFAULT_OPACITY))

        flat_hover = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.06)"

        self.parent.card.setStyleSheet(
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

        self.parent.title_lbl.setFont(QFont(TC.FONT_FAMILY, fs + 1, QFont.Weight.Bold))

        self.parent.fab.setStyleSheet(
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

    def populate_tasks(self, tasks, dark, font_size):
        while self.parent.task_layout.count():
            item = self.parent.task_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        theme = TC.get_theme(dark)

        for task in tasks:
            row = TaskItemWidget(task, dark, font_size)
            row.toggled.connect(self.parent._toggle_task)
            row.deleted.connect(self.parent._delete_task)
            row.important_toggled.connect(self.parent._toggle_task_importance)
            self.parent.task_layout.addWidget(row)

        if not tasks:
            lbl = QLabel("Nothing to do — hit + to add a task!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {theme['text_muted']}; padding: 20px;")
            self.parent.task_layout.addWidget(lbl)
