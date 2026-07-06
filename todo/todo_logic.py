from datetime import datetime

from shared.startup_manager import StartupManager
from todo import todo_theme as TC


class NotificationManager:
    @staticmethod
    def send(title: str, message: str):
        try:
            from winotify import Notification, audio

            toast = Notification(
                app_id="DesktopTodo", title=title, msg=message, duration="short"
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


def filter_tasks(tasks: list, category: str) -> list:
    if category == "important":
        filtered = [t for t in tasks if t.is_important]
    elif category == "all":
        filtered = list(tasks)
    else:
        filtered = [t for t in tasks if t.category == category]

    pending = sorted(
        [t for t in filtered if not t.completed],
        key=lambda t: (
            0 if t.due else 1 if t.is_important else 2,
            not t.is_overdue if t.due else False,
            t.due or "9999",
            t.title.lower(),
        ),
    )
    done = [t for t in filtered if t.completed]
    return pending + done
