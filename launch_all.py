"""
launch_all.py — Start both the To-Do widget and Calendar widget together.

Run this instead of running each file separately:
    python launch_all.py

Both widgets will appear on the desktop and share theme_config.py.
Both will have their own tray icons.
Closing either widget hides it to tray (they don't kill each other).
Right-click either tray icon → Exit to close that widget.
"""

import sys

from PyQt6.QtWidgets import QApplication

from calendar.cal_widget import CalendarWidget
from todo.todo_widget import DesktopTodoWidget


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    todo = DesktopTodoWidget()
    calendar = CalendarWidget()

    todo.show()
    calendar.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
