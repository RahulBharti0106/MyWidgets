import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

from todo import todo_theme as TC
from todo.todo_data import DATA_FILE, SETTINGS_FILE, StorageManager


load_dotenv()


class SyncManager(QThread):
    """
    Runs as a background QThread inside the desktop widget.
    Every 60 seconds:
    1. GET /tasks/sync?since=<last_sync_timestamp> from server
    2. Merge server response into local tasks.json
    3. Push local pending changes to the server
    4. Save last_sync_timestamp = server_time
    5. Emit tasks_updated so the widget UI refreshes
    """

    tasks_updated = pyqtSignal()

    SETTINGS_SYNC_KEY = "last_sync_timestamp"
    SETTINGS_PENDING_DELETES_KEY = "pending_deletions"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server_url = os.getenv("SERVER_URL", "").strip().rstrip("/")
        self._api_key = os.getenv("API_KEY", "").strip()

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(UTC).replace(tzinfo=None).isoformat()

    @staticmethod
    def _parse_iso(value: str | None) -> datetime:
        if not value:
            return datetime.min
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.min

    @staticmethod
    def _load_tasks_payload() -> list[dict]:
        if not DATA_FILE.exists():
            return []
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("tasks", [])
        except (json.JSONDecodeError, KeyError):
            return []

    @staticmethod
    def _write_tasks_payload(tasks_payload: list[dict]):
        with StorageManager._lock:
            tmp = DATA_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"tasks": tasks_payload}, f, indent=2)
            tmp.replace(DATA_FILE)

    @staticmethod
    def _load_settings_payload() -> dict:
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
            return defaults
        except (json.JSONDecodeError, KeyError):
            return defaults

    @staticmethod
    def _save_settings_payload(settings: dict):
        with StorageManager._lock:
            tmp = SETTINGS_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            tmp.replace(SETTINGS_FILE)

    @classmethod
    def save_local_tasks(cls, tasks: list, dirty_ids: set[str] | None = None):
        dirty_ids = dirty_ids or set()
        existing_map = {task["id"]: task for task in cls._load_tasks_payload()}
        payload = []

        for task in tasks:
            record = dict(existing_map.get(task.id, {}))
            record.update(task.to_dict())
            record["updated_at"] = (
                cls._utc_now_iso()
                if task.id in dirty_ids
                else record.get("updated_at", record.get("created", cls._utc_now_iso()))
            )
            if task.id in dirty_ids:
                record["pending_sync"] = True
            elif record.get("pending_sync"):
                record["pending_sync"] = True
            payload.append(record)

        cls._write_tasks_payload(payload)

    @classmethod
    def queue_delete(cls, task_id: str):
        settings = cls._load_settings_payload()
        pending = settings.get(cls.SETTINGS_PENDING_DELETES_KEY, [])
        if task_id not in pending:
            pending.append(task_id)
        settings[cls.SETTINGS_PENDING_DELETES_KEY] = pending
        cls._save_settings_payload(settings)

    def stop(self):
        self.requestInterruption()
        self.wait(2000)

    def run(self):
        while not self.isInterruptionRequested():
            try:
                self._sync_once()
            except Exception as exc:
                print(f"Sync skipped: unexpected sync error ({exc})")

            for _ in range(60):
                if self.isInterruptionRequested():
                    return
                self.sleep(1)

    def _sync_once(self):
        if not self._server_url or not self._api_key:
            print("Sync skipped: SERVER_URL/API_KEY not configured")
            return

        settings = self._load_settings_payload()
        last_sync_timestamp = settings.get(self.SETTINGS_SYNC_KEY, "1970-01-01T00:00:00")
        pending_deletions = set(settings.get(self.SETTINGS_PENDING_DELETES_KEY, []))

        with httpx.Client(
            base_url=self._server_url,
            headers={"X-API-Key": self._api_key},
            timeout=10.0,
        ) as client:
            try:
                response = client.get("/tasks/sync", params={"since": last_sync_timestamp})
                response.raise_for_status()
                sync_payload = response.json()
            except httpx.HTTPError as exc:
                print(f"Sync failed: could not reach server ({exc})")
                return

            local_tasks = self._load_tasks_payload()
            local_order = [task["id"] for task in local_tasks]
            local_map = {task["id"]: dict(task) for task in local_tasks}
            changed = False

            for server_task in sync_payload.get("tasks", []):
                task_id = server_task["id"]
                if task_id in pending_deletions and not server_task.get("deleted", False):
                    continue

                if server_task.get("deleted", False):
                    if task_id in local_map:
                        local_map.pop(task_id, None)
                        local_order = [item for item in local_order if item != task_id]
                        changed = True
                    if task_id in pending_deletions:
                        pending_deletions.discard(task_id)
                    continue

                server_record = self._server_to_local_record(server_task)
                if task_id not in local_map:
                    local_map[task_id] = server_record
                    local_order.append(task_id)
                    changed = True
                    continue

                local_updated = self._parse_iso(
                    local_map[task_id].get("updated_at") or local_map[task_id].get("created")
                )
                server_updated = self._parse_iso(server_task.get("updated_at"))
                if server_updated >= local_updated and local_map[task_id] != server_record:
                    local_map[task_id] = server_record
                    changed = True

            for task_id in list(local_order):
                task = local_map.get(task_id)
                if task is None or not task.get("pending_sync"):
                    continue

                payload = {
                    "id": task["id"],
                    "title": task["title"],
                    "category": task.get("category", "general"),
                    "is_important": task.get("is_important", False),
                    "due": task.get("due"),
                    "created_at": task.get("created"),
                }
                try:
                    response = client.post("/tasks", json=payload)
                    if response.status_code == 409:
                        patch_payload = {
                            "title": task["title"],
                            "category": task.get("category", "general"),
                            "is_important": task.get("is_important", False),
                            "due": task.get("due"),
                            "completed": task.get("completed", False),
                            "reminder_sent": task.get("reminder_sent", False),
                        }
                        response = client.patch(f"/tasks/{task_id}", json=patch_payload)
                    response.raise_for_status()
                    local_map[task_id] = self._server_to_local_record(response.json())
                    changed = True
                except httpx.HTTPError as exc:
                    print(f"Push failed for task {task_id}: {exc}")
                    continue

            for task_id in list(pending_deletions):
                try:
                    response = client.delete(f"/tasks/{task_id}")
                    if response.status_code in (200, 404):
                        pending_deletions.discard(task_id)
                except httpx.HTTPError as exc:
                    print(f"Delete sync skipped for task {task_id}: {exc}")
                    continue

        merged_tasks = [local_map[task_id] for task_id in local_order if task_id in local_map]
        self._write_tasks_payload(merged_tasks)
        settings[self.SETTINGS_SYNC_KEY] = sync_payload.get(
            "server_time", last_sync_timestamp
        )
        settings[self.SETTINGS_PENDING_DELETES_KEY] = list(pending_deletions)
        self._save_settings_payload(settings)

        if changed:
            self.tasks_updated.emit()

    @staticmethod
    def _server_to_local_record(server_task: dict) -> dict:
        return {
            "id": server_task["id"],
            "title": server_task["title"],
            "list_name": TC.DEFAULT_LIST_NAME,
            "due": server_task.get("due"),
            "completed": server_task.get("completed", False),
            "reminder_sent": server_task.get("reminder_sent", False),
            "created": server_task.get("created_at", SyncManager._utc_now_iso()),
            "updated_at": server_task.get("updated_at", SyncManager._utc_now_iso()),
            "category": server_task.get("category", "general"),
            "is_important": server_task.get("is_important", False),
            "pending_sync": False,
        }
