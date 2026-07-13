import hashlib
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from sqlmodel import Field, Relationship, SQLModel, Session, create_engine, select


load_dotenv()


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


def generate_api_key(telegram_id: int, created_at: str) -> str:
    secret = os.getenv("API_SECRET_KEY", "")
    if not secret:
        raise RuntimeError(
            "API_SECRET_KEY is required to generate API keys. "
            "Set API_SECRET_KEY in the environment before using /auth/register."
        )
    raw = f"{secret}{telegram_id}{created_at}{secrets.token_hex(8)}"
    return "mw_" + hashlib.sha256(raw.encode()).hexdigest()[:32]


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True, index=True)
    username: Optional[str] = None
    api_key: str = Field(unique=True, index=True)
    created_at: str
    tasks: List["Task"] = Relationship(back_populates="user")


class Task(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    category: str = Field(default="general")
    is_important: bool = Field(default=False)
    due: Optional[str] = None
    completed: bool = Field(default=False)
    reminder_sent: bool = Field(default=False)
    created_at: str
    updated_at: str
    deleted: bool = Field(default=False)
    user: Optional[User] = Relationship(back_populates="tasks")


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URL = f"sqlite:///{(BASE_DIR / 'mywidgets.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)


def parse_allowed_telegram_ids() -> List[int]:
    raw = os.getenv("ALLOWED_TELEGRAM_IDS", "")
    result: List[int] = []
    for value in raw.split(","):
        cleaned = value.strip()
        if not cleaned:
            continue
        try:
            result.append(int(cleaned))
        except ValueError:
            continue
    return result


def seed_first_user():
    with Session(engine) as session:
        existing = session.exec(select(User)).first()
        if existing is not None:
            return

        allowed_ids = parse_allowed_telegram_ids()
        if not allowed_ids:
            raise RuntimeError(
                "ALLOWED_TELEGRAM_IDS is required to seed the first user. "
                "Set ALLOWED_TELEGRAM_IDS in the environment before starting the server."
            )

        created_at = utc_now_iso()
        telegram_id = allowed_ids[0]
        api_key = generate_api_key(telegram_id, created_at)
        user = User(
            telegram_id=telegram_id,
            username=None,
            api_key=api_key,
            created_at=created_at,
        )
        session.add(user)
        session.commit()
        print(f"\n[MyWidgets] Seeded owner user. API key: {api_key}\n")
