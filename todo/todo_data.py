import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from todo import todo_theme as TC


APP_NAME = "DesktopTodo"
DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / APP_NAME
DATA_FILE = DATA_DIR / "tasks.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


class Task:
    def __init__(
        self,
        title: str,
        list_name: str = None,
        due: str = None,
        task_id: str = None,
        completed: bool = False,
        reminder_sent: bool = False,
        category: str = "general",
        is_important: bool = False,
    ):
        self.id = task_id or str(uuid.uuid4())
        self.title = title
        self.list_name = list_name or TC.DEFAULT_LIST_NAME
        self.due = due
        self.completed = completed
        self.reminder_sent = reminder_sent
        self.category = category
        self.is_important = is_important
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
            "category": self.category,
            "is_important": self.is_important,
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
            category=d.get("category", "general"),
            is_important=d.get("is_important", False),
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
