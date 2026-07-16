import os
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


load_dotenv()


ADD_TITLE, ADD_CATEGORY, ADD_DUE, ADD_CUSTOM_DATE = range(4)
LIST_PAGE_SIZE = 5
_http_client: Optional[httpx.AsyncClient] = None


def build_bot_application() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    owner_api_key = os.getenv("OWNER_API_KEY", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is required to start the Telegram bot."
        )
    if not owner_api_key:
        raise RuntimeError(
            "OWNER_API_KEY is required so the bot can call the internal API."
        )

    allowed_ids = _parse_allowed_telegram_ids()
    port = int(os.getenv("PORT", 8000))
    base_url = f"http://127.0.0.1:{port}"

    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=base_url,
        headers={"X-API-Key": owner_api_key},
        timeout=10.0,
    )

    application = ApplicationBuilder().token(token).build()
    application.bot_data["allowed_ids"] = allowed_ids
    application.bot_data["http_client"] = _http_client

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            ADD_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_title)
            ],
            ADD_CATEGORY: [
                CallbackQueryHandler(add_choose_category, pattern=r"^addcat:")
            ],
            ADD_DUE: [CallbackQueryHandler(add_choose_due, pattern=r"^adddue:")],
            ADD_CUSTOM_DATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, add_receive_custom_date
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("important", important_command))
    application.add_handler(add_conv)
    application.add_handler(
        CallbackQueryHandler(list_page_callback, pattern=r"^listpage:")
    )
    application.add_handler(
        CallbackQueryHandler(action_page_callback, pattern=r"^actionpage:")
    )
    application.add_handler(
        CallbackQueryHandler(action_select_callback, pattern=r"^actionselect:")
    )

    return application


def _parse_allowed_telegram_ids() -> set[int]:
    raw = os.getenv("ALLOWED_TELEGRAM_IDS", "")
    result: set[int] = set()
    for value in raw.split(","):
        cleaned = value.strip()
        if not cleaned:
            continue
        try:
            result.add(int(cleaned))
        except ValueError:
            continue
    return result


async def _ensure_allowed(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    user = update.effective_user
    allowed_ids = context.application.bot_data.get("allowed_ids", set())
    if user is not None and user.id in allowed_ids:
        return True

    message = "Access is restricted for this bot."
    if update.message is not None:
        await update.message.reply_text(message)
    elif update.callback_query is not None:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message)
    return False


async def _api_request(
    context: ContextTypes.DEFAULT_TYPE,
    method: str,
    path: str,
    *,
    json_data: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
) -> tuple[bool, Any]:
    client: httpx.AsyncClient = context.application.bot_data["http_client"]
    try:
        response = await client.request(method, path, json=json_data, params=params)
        response.raise_for_status()
        return True, response.json()
    except httpx.HTTPStatusError as exc:
        try:
            payload = exc.response.json()
            detail = payload.get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        return False, f"API error {exc.response.status_code}: {detail}"
    except httpx.HTTPError as exc:
        return False, f"Network error: {exc}"


def _due_from_choice(choice: str) -> tuple[Optional[str], str]:
    now = datetime.now(UTC)
    if choice == "none":
        return None, "no due date"
    if choice == "today":
        due = now.replace(hour=23, minute=59, second=0, microsecond=0)
        return due.replace(tzinfo=None).isoformat(), "today"
    if choice == "tomorrow":
        due = (now + timedelta(days=1)).replace(
            hour=23, minute=59, second=0, microsecond=0
        )
        return due.replace(tzinfo=None).isoformat(), "tomorrow"
    due = (now + timedelta(days=max(1, 6 - now.weekday()))).replace(
        hour=23, minute=59, second=0, microsecond=0
    )
    return due.replace(tzinfo=None).isoformat(), "this week"


def _create_add_payload(context: ContextTypes.DEFAULT_TYPE, due_iso: Optional[str]) -> dict[str, Any]:
    task_data = context.user_data.get("add_task", {})
    return {
        "title": task_data["title"],
        "category": task_data["category"],
        "is_important": False,
        "due": due_iso,
    }


def _parse_custom_due_input(raw_value: str) -> Optional[str]:
    value = raw_value.strip()
    formats = [
        ("%d/%m/%Y %H:%M", True),
        ("%d/%m/%Y", False),
    ]
    for fmt, has_time in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if not has_time:
                parsed = parsed.replace(hour=23, minute=59, second=0, microsecond=0)
            else:
                parsed = parsed.replace(second=0, microsecond=0)
            return parsed.isoformat()
        except ValueError:
            continue
    return None


def _format_task_lines(tasks: list[dict[str, Any]], offset: int = 0) -> str:
    lines = []
    for index, task in enumerate(tasks, start=1 + offset):
        important = "★ " if task.get("is_important") else ""
        due = f" | due {task['due'][:10]}" if task.get("due") else ""
        lines.append(f"{index}. {important}{task['title']}{due}")
    return "\n".join(lines) if lines else "No tasks found."


def _pagination_keyboard(
    page: int, total: int, prefix: str
) -> Optional[InlineKeyboardMarkup]:
    row = []
    if page > 0:
        row.append(
            InlineKeyboardButton("◀️ Prev", callback_data=f"{prefix}:{page - 1}")
        )
    if (page + 1) * LIST_PAGE_SIZE < total:
        row.append(
            InlineKeyboardButton("Next ▶️", callback_data=f"{prefix}:{page + 1}")
        )
    return InlineKeyboardMarkup([row]) if row else None


def _action_keyboard(
    action: str, tasks: list[dict[str, Any]], page: int, total: int
) -> InlineKeyboardMarkup:
    buttons = []
    offset = page * LIST_PAGE_SIZE
    for index, task in enumerate(tasks, start=1 + offset):
        buttons.append(
            [
                InlineKeyboardButton(
                    str(index),
                    callback_data=f"actionselect:{action}:{task['id']}",
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                "◀️ Prev", callback_data=f"actionpage:{action}:{page - 1}"
            )
        )
    if (page + 1) * LIST_PAGE_SIZE < total:
        nav.append(
            InlineKeyboardButton(
                "Next ▶️", callback_data=f"actionpage:{action}:{page + 1}"
            )
        )
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


async def _fetch_incomplete_tasks(
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[bool, Any]:
    return await _api_request(
        context,
        "GET",
        "/tasks",
        params={"completed": "false"},
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_allowed(update, context):
        return
    await update.message.reply_text(
        "Welcome to MyWidgets bot.\n\n"
        "Commands:\n"
        "/add - add a task\n"
        "/list - list incomplete tasks\n"
        "/done - mark a task complete\n"
        "/delete - delete a task\n"
        "/important - toggle important\n"
        "/today - show tasks due today\n"
        "/help - show help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_allowed(update, context):
        return
    await update.message.reply_text(
        "/start\n"
        "/add\n"
        "/list\n"
        "/done\n"
        "/delete\n"
        "/important\n"
        "/today\n"
        "/help"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("add_task", None)
    if update.message is not None:
        await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _ensure_allowed(update, context):
        return ConversationHandler.END
    context.user_data["add_task"] = {}
    await update.message.reply_text("What's the task?")
    return ADD_TITLE


async def add_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["add_task"] = {"title": update.message.text.strip()}
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("General", callback_data="addcat:general"),
                InlineKeyboardButton("Work", callback_data="addcat:work"),
            ],
            [
                InlineKeyboardButton("Study", callback_data="addcat:study"),
                InlineKeyboardButton("Personal", callback_data="addcat:personal"),
            ],
        ]
    )
    await update.message.reply_text("Choose a category:", reply_markup=keyboard)
    return ADD_CATEGORY


async def add_choose_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault("add_task", {})["category"] = query.data.split(":", 1)[1]
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Today", callback_data="adddue:today"),
                InlineKeyboardButton("Tomorrow", callback_data="adddue:tomorrow"),
            ],
            [
                InlineKeyboardButton("This week", callback_data="adddue:week"),
                InlineKeyboardButton("No due date", callback_data="adddue:none"),
            ],
            [
                InlineKeyboardButton(
                    "📅 Custom date", callback_data="adddue:custom"
                )
            ],
        ]
    )
    await query.edit_message_text("Choose a due date:", reply_markup=keyboard)
    return ADD_DUE


async def add_choose_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":", 1)[1]
    if choice == "custom":
        await query.edit_message_text(
            "Enter the due date in DD/MM/YYYY format (e.g. 25/12/2026). "
            "You can also add a time like DD/MM/YYYY HH:MM."
        )
        return ADD_CUSTOM_DATE
    due_iso, due_label = _due_from_choice(choice)
    payload = _create_add_payload(context, due_iso)
    ok, result = await _api_request(context, "POST", "/tasks", json_data=payload)
    context.user_data.pop("add_task", None)
    if not ok:
        await query.edit_message_text(f"Could not add task. {result}")
        return ConversationHandler.END
    await query.edit_message_text(
        f'✅ Added "{result["title"]}" to {result["category"]}, due {due_label}.'
    )
    return ConversationHandler.END


async def add_receive_custom_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    due_iso = _parse_custom_due_input(update.message.text)
    if due_iso is None:
        await update.message.reply_text(
            "Couldn't understand that date. Please use DD/MM/YYYY "
            "(e.g. 25/12/2026)."
        )
        return ADD_CUSTOM_DATE

    payload = _create_add_payload(context, due_iso)
    ok, result = await _api_request(context, "POST", "/tasks", json_data=payload)
    context.user_data.pop("add_task", None)
    if not ok:
        await update.message.reply_text(f"Could not add task. {result}")
        return ConversationHandler.END

    await update.message.reply_text(
        f'✅ Added "{result["title"]}" to {result["category"]}, due {due_iso[:16]}.'
    )
    return ConversationHandler.END


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_allowed(update, context):
        return
    await _send_task_list_page(update.message, context, 0)


async def _send_task_list_page(
    message_target: Any, context: ContextTypes.DEFAULT_TYPE, page: int
) -> None:
    ok, result = await _fetch_incomplete_tasks(context)
    if not ok:
        await message_target.reply_text(f"Could not load tasks. {result}")
        return
    tasks = result
    start_index = page * LIST_PAGE_SIZE
    chunk = tasks[start_index : start_index + LIST_PAGE_SIZE]
    await message_target.reply_text(
        _format_task_lines(chunk, offset=start_index),
        reply_markup=_pagination_keyboard(page, len(tasks), "listpage"),
    )


async def list_page_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await _ensure_allowed(update, context):
        return
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    ok, result = await _fetch_incomplete_tasks(context)
    if not ok:
        await query.edit_message_text(f"Could not load tasks. {result}")
        return
    tasks = result
    start_index = page * LIST_PAGE_SIZE
    chunk = tasks[start_index : start_index + LIST_PAGE_SIZE]
    await query.edit_message_text(
        _format_task_lines(chunk, offset=start_index),
        reply_markup=_pagination_keyboard(page, len(tasks), "listpage"),
    )


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_allowed(update, context):
        return
    await _send_action_page(update.message, context, "done", 0)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_allowed(update, context):
        return
    await _send_action_page(update.message, context, "delete", 0)


async def important_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await _ensure_allowed(update, context):
        return
    await _send_action_page(update.message, context, "important", 0)


async def _send_action_page(
    message_target: Any,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    page: int,
) -> None:
    ok, result = await _fetch_incomplete_tasks(context)
    if not ok:
        await message_target.reply_text(f"Could not load tasks. {result}")
        return
    tasks = result
    if not tasks:
        await message_target.reply_text("No incomplete tasks.")
        return
    start_index = page * LIST_PAGE_SIZE
    chunk = tasks[start_index : start_index + LIST_PAGE_SIZE]
    await message_target.reply_text(
        _format_task_lines(chunk, offset=start_index),
        reply_markup=_action_keyboard(action, chunk, page, len(tasks)),
    )


async def action_page_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await _ensure_allowed(update, context):
        return
    query = update.callback_query
    await query.answer()
    _, action, page_str = query.data.split(":")
    page = int(page_str)
    ok, result = await _fetch_incomplete_tasks(context)
    if not ok:
        await query.edit_message_text(f"Could not load tasks. {result}")
        return
    tasks = result
    if not tasks:
        await query.edit_message_text("No incomplete tasks.")
        return
    start_index = page * LIST_PAGE_SIZE
    chunk = tasks[start_index : start_index + LIST_PAGE_SIZE]
    await query.edit_message_text(
        _format_task_lines(chunk, offset=start_index),
        reply_markup=_action_keyboard(action, chunk, page, len(tasks)),
    )


async def action_select_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await _ensure_allowed(update, context):
        return
    query = update.callback_query
    await query.answer()
    _, action, task_id = query.data.split(":")

    ok, tasks_result = await _fetch_incomplete_tasks(context)
    if not ok:
        await query.edit_message_text(f"Could not load tasks. {tasks_result}")
        return
    task = next((item for item in tasks_result if item["id"] == task_id), None)
    if task is None:
        await query.edit_message_text("Task not found.")
        return

    if action == "done":
        ok, result = await _api_request(
            context,
            "PATCH",
            f"/tasks/{task_id}",
            json_data={"completed": True},
        )
        if not ok:
            await query.edit_message_text(f"Could not update task. {result}")
            return
        await query.edit_message_text(f'✅ Marked "{result["title"]}" as done.')
        return

    if action == "delete":
        ok, result = await _api_request(context, "DELETE", f"/tasks/{task_id}")
        if not ok:
            await query.edit_message_text(f"Could not delete task. {result}")
            return
        await query.edit_message_text(f'🗑 Deleted "{task["title"]}".')
        return

    ok, result = await _api_request(
        context,
        "PATCH",
        f"/tasks/{task_id}",
        json_data={"is_important": not task.get("is_important", False)},
    )
    if not ok:
        await query.edit_message_text(f"Could not update task. {result}")
        return
    state = "important" if result["is_important"] else "not important"
    await query.edit_message_text(f'⭐ Marked "{result["title"]}" as {state}.')


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_allowed(update, context):
        return
    ok, result = await _fetch_incomplete_tasks(context)
    if not ok:
        await update.message.reply_text(f"Could not load tasks. {result}")
        return
    today = datetime.now().date()
    tasks = []
    for task in result:
        due = task.get("due")
        if not due:
            continue
        try:
            if datetime.fromisoformat(due).date() == today:
                tasks.append(task)
        except ValueError:
            continue
    await update.message.reply_text(_format_task_lines(tasks))
