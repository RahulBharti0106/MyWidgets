from typing import List, Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None


class TaskCreate(BaseModel):
    id: Optional[str] = None
    title: str
    category: str = "general"
    is_important: bool = False
    due: Optional[str] = None
    created_at: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    is_important: Optional[bool] = None
    due: Optional[str] = None
    completed: Optional[bool] = None
    reminder_sent: Optional[bool] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    category: str
    is_important: bool
    due: Optional[str]
    completed: bool
    reminder_sent: bool
    created_at: str
    updated_at: str
    deleted: bool


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    api_key: str
    created_at: str


class SyncResponse(BaseModel):
    tasks: List[TaskResponse]
    server_time: str


class RegisterResponse(BaseModel):
    api_key: str
    message: str
