import os
import logging
import logging.config
from configparser import ConfigParser
from pathlib import Path
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import aioredis
from fastapi import FastAPI, Depends
import uvicorn

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.api.routes import router as api_router
from app.bot.handlers import register_handlers

def load_config(path: str) -> ConfigParser:
    config = ConfigParser()
    files = config.read(path)
    if not files:
        raise FileNotFoundError(f"Configuration file not found: {path}")
    return config

def validate_config(config: ConfigParser):
    required = {
        'database': ['url'],
        'redis': ['url'],
        'telegram': ['token'],
    }
    missing = []
    for section, keys in required.items():
        if not config.has_section(section):
            missing.append(f"Missing section: [{section}]")
        else:
            for key in keys:
                if not config.has_option(section, key):
                    missing.append(f"Missing option '{key}' in section [{section}]")
    if missing:
        raise ValueError("Configuration validation error:\n" + "\n".join(missing))

def init_logging(path: str):
    if Path(path).exists():
        logging.config.fileConfig(path, disable_existing_loggers=False)
    else:
        logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("Logging initialized")

def init_db(db_url: str, echo: bool = False):
    engine = create_async_engine(db_url, echo=echo, future=True)
    SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, SessionLocal

def init_cache(redis_url: str):
    return aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)

def create_app(config: ConfigParser, engine, SessionLocal, redis_pool):
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except:
                await session.rollback()
                raise

    app = FastAPI(
        title="Belarus Tourism Bot API",
        version=config.get("app", "version", fallback="1.0.0"),
        dependencies=[Depends(get_db)],
    )

    app.include_router(api_router, prefix="/api")

    app.state.config = config
    app.state.db_engine = engine
    app.state.db_session = SessionLocal
    app.state.redis = redis_pool

    bot_token = config.get("telegram", "token")
    storage = RedisStorage.from_url(config.get("redis", "url"))
    bot = Bot(token=bot_token)
    dp = Dispatcher(storage=storage)
    register_handlers(dp)

    @app.on_event("startup")
    async def on_startup():
        async with engine.begin():
            pass
        default_commands = [
            {"command": "start", "description": "Start interaction"},
            {"command": "help", "description": "Get help"},
        ]
        await bot.set_my_commands(default_commands)
        app.state.bot_polling_task = asyncio.create_task(
            dp.start_polling(bot, skip_updates=True)
        )

    @app.on_event("shutdown")
    async def on_shutdown():
        polling_task = getattr(app.state, "bot_polling_task", None)
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()
        try:
            redis_pool.close()
            await redis_pool.wait_closed()
        except Exception:
            pass
        await engine.dispose()

    return app

def main():
    config_path = os.getenv("CONFIG_PATH", "config.ini")
    logging_path = os.getenv("LOGGING_CONFIG_PATH", "logging.ini")
    config = load_config(config_path)
    init_logging(logging_path)
    try:
        validate_config(config)
    except ValueError as e:
        logging.error(str(e))
        raise
    db_url = config.get("database", "url")
    db_echo = config.getboolean("database", "echo", fallback=False)
    engine, SessionLocal = init_db(db_url, db_echo)
    redis_url = config.get("redis", "url")
    redis_pool = init_cache(redis_url)
    app = create_app(config, engine, SessionLocal, redis_pool)
    host = config.get("api", "host", fallback="0.0.0.0")
    port = config.getint("api", "port", fallback=8000)
    log_level = config.get("logging", "level", fallback="info")
    uvicorn.run(app, host=host, port=port, log_level=log_level)

if __name__ == "__main__":
    main()