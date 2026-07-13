import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from bot import build_bot_application
from database import init_db, seed_first_user
from routes import router


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_first_user()

    bot_app = build_bot_application()
    await bot_app.initialize()
    await bot_app.start()
    if bot_app.updater is not None:
        await bot_app.updater.start_polling()

    try:
        yield
    finally:
        if bot_app.updater is not None:
            await bot_app.updater.stop()
        await bot_app.stop()
        http_client = bot_app.bot_data.get("http_client")
        if http_client is not None:
            await http_client.aclose()
        await bot_app.shutdown()


app = FastAPI(
    title="MyWidgets API",
    description="Task sync API for MyWidgets desktop app",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
