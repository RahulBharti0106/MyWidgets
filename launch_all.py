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
