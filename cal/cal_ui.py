from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizeGrip,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cal import cal_theme as TC

DAYS_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


class DayCell(QFrame):
    badge_clicked = pyqtSignal(date, object)

    def __init__(
        self,
        day: int,
        cell_date,
        this_month: bool,
        is_today: bool,
        is_past: bool,
        task_count: int,
        theme: dict,
        font_size: int,
    ):
        super().__init__()
        self._day = day
        self._cell_date = cell_date
        self._this_month = this_month
        self._is_today = is_today
        self._is_past = is_past
        self._task_count = task_count
        self._theme = theme
        self._font_size = font_size

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(28, 28)
        self._badge_btn = None
        self._build()

    def _build(self):
        t = self._theme
        fs = self._font_size

        if not self._day:
            self.setStyleSheet("background: transparent; border: none;")
            return

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
        radius = max(6, fs // 2)

        self.setStyleSheet(f"""
            DayCell {{
                background:    {bg};
                border:        none;
                border-radius: {radius}px;
            }}
            DayCell:hover {{
                background:    {hover_bg};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl = QLabel(str(self._day))
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._lbl.setStyleSheet(f"""
            color:           {fg};
            font-size:       {fs}px;
            font-family:     '{TC.FONT_FAMILY}';
            font-weight:     {weight};
            text-decoration: {strike};
            background:      transparent;
        """)
        layout.addWidget(self._lbl)

        if self._task_count > 0 and self._this_month and not self._is_past:
            self._badge_btn = QPushButton(str(self._task_count), self)
            self._badge_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._badge_btn.setMinimumWidth(16)
            self._badge_btn.setFixedHeight(14)
            self._badge_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(239,223,10,0.2);
                    color: {t["dot_color"]};
                    font-size: 9px;
                    border-radius: 6px;
                    border: none;
                    padding: 0 4px;
                }}
            """)
            self._badge_btn.clicked.connect(
                lambda: self.badge_clicked.emit(self._cell_date, self._badge_btn)
            )
            self._badge_btn.adjustSize()
            self._badge_btn.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._badge_btn:
            margin = max(3, self._font_size // 5)
            self._badge_btn.move(
                self.width() - self._badge_btn.width() - margin,
                margin,
            )


class CalUI:
    def __init__(self, parent):
        self.parent = parent
        self._build_ui(parent)

    def _build_ui(self, parent):
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(0, 0, 0, 0)

        parent.card = QFrame(parent)
        parent.card.setObjectName("card")
        parent._card_layout = QVBoxLayout(parent.card)
        parent._card_layout.setContentsMargins(14, 12, 14, 10)
        parent._card_layout.setSpacing(6)

        nav = QHBoxLayout()
        nav.setSpacing(6)

        parent._prev_btn = QPushButton("‹")
        parent._prev_btn.setFixedSize(32, 32)
        parent._prev_btn.setToolTip("Previous month")
        parent._prev_btn.clicked.connect(parent._go_prev)
        nav.addWidget(parent._prev_btn)

        parent._month_lbl = QPushButton("")
        parent._month_lbl.setFlat(True)
        parent._month_lbl.setToolTip("Click to jump to a month")
        parent._month_lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        parent._month_lbl.clicked.connect(parent._jump_to_month)
        nav.addWidget(parent._month_lbl, stretch=1)

        parent._next_btn = QPushButton("›")
        parent._next_btn.setFixedSize(32, 32)
        parent._next_btn.setToolTip("Next month")
        parent._next_btn.clicked.connect(parent._go_next)
        nav.addWidget(parent._next_btn)

        parent._today_btn = QPushButton("Today")
        parent._today_btn.setFixedHeight(32)
        parent._today_btn.setToolTip("Jump to today")
        parent._today_btn.clicked.connect(parent._go_today)
        nav.addWidget(parent._today_btn)

        parent._settings_btn = QPushButton("⚙")
        parent._settings_btn.setFixedSize(32, 32)
        parent._settings_btn.setFlat(True)
        parent._settings_btn.setToolTip("Settings")
        parent._settings_btn.clicked.connect(parent._open_settings)
        nav.addWidget(parent._settings_btn)

        parent._card_layout.addLayout(nav)

        parent._weekday_row = QHBoxLayout()
        parent._weekday_row.setSpacing(4)
        parent._weekday_labels = []
        for d in DAYS_SHORT:
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            parent._weekday_labels.append(lbl)
            parent._weekday_row.addWidget(lbl)
        parent._card_layout.addLayout(parent._weekday_row)

        parent._grid_container = QWidget()
        parent._grid_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        parent._grid_layout = QGridLayout(parent._grid_container)
        parent._grid_layout.setSpacing(4)
        parent._grid_layout.setContentsMargins(0, 0, 0, 0)
        for col in range(7):
            parent._grid_layout.setColumnStretch(col, 1)
        parent._card_layout.addWidget(parent._grid_container, stretch=1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        grip = QSizeGrip(parent.card)
        grip.setFixedSize(16, 16)
        bottom.addWidget(grip)
        parent._card_layout.addLayout(bottom)

        outer.addWidget(parent.card)

    def apply_theme(self, settings):
        dark = True
        t = TC.get_cal_theme(dark)
        self.parent.setWindowOpacity(settings.get("opacity", 0.92))

        self.parent.card.setStyleSheet(f"""
            QFrame#card {{
                background:    {t["card_bg"]};
                border:        1px solid {t["border"]};
                border-radius: {t["card_radius"]};
            }}
            QLabel {{
                color:      {t["text"]};
                background: transparent;
            }}
        """)

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
        self.parent._prev_btn.setStyleSheet(nav_style)
        self.parent._next_btn.setStyleSheet(nav_style)

        self.parent._month_lbl.setStyleSheet(f"""
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
        """)

        self.parent._today_btn.setStyleSheet(f"""
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
        """)

        self.parent._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {t["text_muted"]};
                border: none; font-size: 15px;
            }}
            QPushButton:hover {{ color: {t["text"]}; }}
        """)

        for lbl in self.parent._weekday_labels:
            lbl.setStyleSheet(f"""
                color:       {t["weekday_text"]};
                font-size:   11px;
                font-family: '{TC.FONT_FAMILY}';
                font-weight: bold;
            """)

    def rebuild_grid(self, year, month, today, task_counts):
        while self.parent._grid_layout.count():
            item = self.parent._grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.hide()

        dark = True
        t = TC.get_cal_theme(dark)

        cell_w = max(28, (self.parent.width() - 28) // 7)
        fs = max(10, min(26, int(cell_w * 0.35)))
        gap = max(2, cell_w // 12)
        self.parent._grid_layout.setSpacing(gap)

        for lbl in self.parent._weekday_labels:
            lbl.setStyleSheet(
                lbl.styleSheet().split("font-size")[0]
                + f"font-size: {max(9, fs - 3)}px; font-family: '{TC.FONT_FAMILY}'; font-weight: bold;"
            )

        cal = self.parent._month_calendar_sunday_first(year, month)
        month_name = date(year, month, 1).strftime("%B %Y")
        self.parent._month_lbl.setText(f"  {month_name}")

        for row_idx, week in enumerate(cal):
            self.parent._grid_layout.setRowStretch(row_idx, 1)
            for col_idx, day in enumerate(week):
                if day == 0:
                    cell = DayCell(0, None, False, False, False, 0, t, fs)
                else:
                    cell_date = date(year, month, day)
                    is_today = cell_date == today
                    is_past = cell_date < today
                    task_count = task_counts.get(cell_date, 0)
                    cell = DayCell(
                        day,
                        cell_date,
                        True,
                        is_today,
                        is_past,
                        task_count,
                        t,
                        fs,
                    )
                    cell.badge_clicked.connect(self.parent._open_day_popup)
                self.parent._grid_layout.addWidget(cell, row_idx, col_idx)
        for empty_row in range(len(cal), 6):
            self.parent._grid_layout.setRowStretch(empty_row, 0)
