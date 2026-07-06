import json
import os
import threading
from datetime import datetime
from pathlib import Path

from calendar import cal_theme as TC


APP_NAME = "DesktopCalendar"
TODO_APP_NAME = "DesktopTodo"

DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / APP_NAME
SETTINGS_FILE = DATA_DIR / "settings.json"
TODO_TASKS = Path(os.getenv("APPDATA", Path.home())) / TODO_APP_NAME / "tasks.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


class CalStorage:
    _lock = threading.Lock()

    @staticmethod
    def load_settings() -> dict:
        defaults = {
            "x": 460,
            "y": 100,
            "width": 380,
            "height": 400,
            "opacity": TC.DEFAULT_OPACITY,
            "startup": TC.DEFAULT_STARTUP,
        }
        if not SETTINGS_FILE.exists():
            return defaults
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            defaults.update(loaded)
            return defaults
        except Exception:
            return defaults

    @staticmethod
    def save_settings(s: dict):
        with CalStorage._lock:
            tmp = SETTINGS_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2)
            tmp.replace(SETTINGS_FILE)

    @staticmethod
    def load_task_counts() -> dict:
        if not TODO_TASKS.exists():
            return {}
        try:
            with open(TODO_TASKS, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = {}
            for t in data.get("tasks", []):
                if t.get("due") and not t.get("completed", False):
                    try:
                        due_date = datetime.fromisoformat(t["due"]).date()
                        result[due_date] = result.get(due_date, 0) + 1
                    except ValueError:
                        pass
            return result
        except Exception:
            return {}
