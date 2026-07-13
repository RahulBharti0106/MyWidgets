import uuid
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from auth import get_current_user
from database import (
    Task,
    User,
    generate_api_key,
    get_session,
    parse_allowed_telegram_ids,
    utc_now_iso,
)
from schemas import (
    RegisterRequest,
    RegisterResponse,
    SyncResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)


load_dotenv()


router = APIRouter()


def to_task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        category=task.category,
        is_important=task.is_important,
        due=task.due,
        completed=task.completed,
        reminder_sent=task.reminder_sent,
        created_at=task.created_at,
        updated_at=task.updated_at,
        deleted=task.deleted,
    )


def validate_iso_datetime(value: str, field_name: str) -> None:
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISO datetime for {field_name}",
        ) from exc


@router.get("/health")
def health_check():
    return {"status": "ok", "time": utc_now_iso()}


@router.post("/auth/register", response_model=RegisterResponse)
def register_user(payload: RegisterRequest, session: Session = Depends(get_session)):
    allowed_ids = parse_allowed_telegram_ids()
    if payload.telegram_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram ID not allowed",
        )

    existing = session.exec(
        select(User).where(User.telegram_id == payload.telegram_id)
    ).first()
    if existing is not None:
        if payload.username is not None and payload.username != existing.username:
            existing.username = payload.username
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return RegisterResponse(
            api_key=existing.api_key,
            message="Existing API key returned",
        )

    created_at = utc_now_iso()
    api_key = generate_api_key(payload.telegram_id, created_at)
    user = User(
        telegram_id=payload.telegram_id,
        username=payload.username,
        api_key=api_key,
        created_at=created_at,
    )
    session.add(user)
    session.commit()
    return RegisterResponse(api_key=api_key, message="User registered successfully")


@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(
    completed: Optional[bool] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    statement = select(Task).where(Task.user_id == current_user.id, Task.deleted == False)
    if completed is not None:
        statement = statement.where(Task.completed == completed)
    if category is not None:
        statement = statement.where(Task.category == category)
    tasks = session.exec(statement).all()
    return [to_task_response(task) for task in tasks]


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    task_id = payload.id or str(uuid.uuid4())
    existing = session.get(Task, task_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task ID already exists",
        )

    now = payload.created_at or utc_now_iso()
    if payload.due is not None:
        validate_iso_datetime(payload.due, "due")
    if payload.created_at is not None:
        validate_iso_datetime(payload.created_at, "created_at")
    task = Task(
        id=task_id,
        user_id=current_user.id,
        title=payload.title,
        category=payload.category,
        is_important=payload.is_important,
        due=payload.due,
        completed=False,
        reminder_sent=False,
        created_at=now,
        updated_at=now,
        deleted=False,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return to_task_response(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    task = session.get(Task, task_id)
    if task is None or task.user_id != current_user.id or task.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)
    if "due" in updates and updates["due"] is not None:
        validate_iso_datetime(updates["due"], "due")
    for field_name, value in updates.items():
        setattr(task, field_name, value)
    task.updated_at = utc_now_iso()
    session.add(task)
    session.commit()
    session.refresh(task)
    return to_task_response(task)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    task = session.get(Task, task_id)
    if task is None or task.user_id != current_user.id or task.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.deleted = True
    task.updated_at = utc_now_iso()
    session.add(task)
    session.commit()
    return {"deleted": True, "id": task_id}


@router.get("/tasks/sync", response_model=SyncResponse)
def sync_tasks(
    since: str = Query(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    validate_iso_datetime(since, "since")
    tasks = session.exec(
        select(Task).where(Task.user_id == current_user.id, Task.updated_at > since)
    ).all()
    return SyncResponse(
        tasks=[to_task_response(task) for task in tasks],
        server_time=utc_now_iso(),
    )
