# MyWidgets Server

Phase 1 foundation for the MyWidgets desktop app. This server provides a FastAPI REST API backed by SQLModel and Postgres (Neon) for task sync.

## Local Setup

```bash
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in the values in `.env`, then start the server:

```bash
python main.py
```

`DATABASE_URL` is required. The server does not support any local database fallback.

API docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## First Run

- On first startup, the server initializes the database tables.
- If no users exist yet, it auto-creates the owner user using the first ID from `ALLOWED_TELEGRAM_IDS`.
- The seeded owner user gets an auto-generated API key.
- The server prints that key to the console once during initial seeding.
- Save that key as `OWNER_API_KEY` in `.env` for the Telegram bot.
- Send it in the `X-API-Key` header on all authenticated requests.

## Registration Behavior

- `POST /auth/register` is still available.
- If the Telegram user already exists, it returns the existing API key.
- If the Telegram user does not exist yet, the server generates a new API key using `API_SECRET_KEY`.
- The first seeded owner user also gets an auto-generated API key.

## Bot

- The Telegram bot runs in the same process as the FastAPI app.
- It calls the API over `http://127.0.0.1:{PORT}` using `httpx`.
- Required bot env vars:
  - `TELEGRAM_BOT_TOKEN`
  - `OWNER_API_KEY`

Supported commands:

- `/start`
- `/add`
- `/list`
- `/done`
- `/delete`
- `/important`
- `/today`
- `/help`

## Render Deployment

1. Push the `server/` folder to GitHub.
2. Create a new Web Service on Render.
3. Set the root directory to `server`.
4. Set the build command to:

```bash
pip install -r requirements.txt
```

5. Set the start command to:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

6. Add all environment variables from `.env.example` in the Render dashboard.
7. Set `DEBUG=false` on Render.

## API Summary

- `GET /health`
- `POST /auth/register`
- `GET /tasks`
- `POST /tasks`
- `PATCH /tasks/{task_id}`
- `DELETE /tasks/{task_id}`
- `GET /tasks/sync`

## Notes

- Datetimes are stored as UTC ISO strings.
- Task deletes are soft deletes only.
- `/tasks/sync` includes deleted tasks so clients can remove them locally.
- All task routes are scoped to the authenticated user.
- Postgres (Neon) via `DATABASE_URL` is required in every environment.
