import os
import sys
import logging
import asyncio
from typing import List
from pydantic import BaseSettings
import asyncpg
import aioredis
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from handlers.route import register_route_handlers
from handlers.quiz import register_quiz_handlers
from handlers.gamification import register_gamification_handlers
from handlers.geolocation import register_geolocation_handlers

class Settings(BaseSettings):
    BOT_TOKEN: str
    DB_DSN: str
    REDIS_DSN: str
    LOG_LEVEL: str = "INFO"
    ALLOWED_UPDATES: List[str] = ["message", "callback_query", "inline_query"]
    class Config:
        env_file = ".env"

settings = Settings()
logger = logging.getLogger(__name__)

class BotApp:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.storage = RedisStorage.from_url(self.settings.REDIS_DSN, prefix="fsm:")
        self.bot = Bot(token=self.settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
        self.dp = Dispatcher(storage=self.storage)
        self.db_pool: asyncpg.Pool = None
        self.redis_client: aioredis.Redis = None

        register_route_handlers(self.dp)
        register_quiz_handlers(self.dp)
        register_gamification_handlers(self.dp)
        register_geolocation_handlers(self.dp)
        logger.info("Handlers registered")

        self.dp.startup.register(self.on_startup)
        self.dp.shutdown.register(self.on_shutdown)

    async def on_startup(self):
        logger.info("Bot startup initiated")
        try:
            self.db_pool = await asyncpg.create_pool(dsn=self.settings.DB_DSN)
            logger.info("PostgreSQL pool created")
            self.redis_client = aioredis.from_url(
                self.settings.REDIS_DSN, encoding="utf-8", decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis client initialized")

            setattr(self.dp, "db_pool", self.db_pool)
            setattr(self.dp, "redis_client", self.redis_client)

            commands = [
                BotCommand(command="start", description="Start the bot"),
                BotCommand(command="help", description="Get help information"),
                BotCommand(command="routes", description="Browse travel routes"),
                BotCommand(command="quiz", description="Take a quiz about Belarus"),
                BotCommand(command="badges", description="View your badges"),
            ]
            await self.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
            logger.info("Bot commands set")
            logger.info("Bot startup completed")
        except Exception as e:
            logger.exception("Error during startup: %s", e)
            if self.redis_client:
                try:
                    await self.redis_client.close()
                    logger.info("Application Redis client closed due to startup failure")
                except Exception:
                    logger.exception("Failed to close Redis client during startup cleanup")
            if self.db_pool:
                try:
                    await self.db_pool.close()
                    logger.info("PostgreSQL pool closed due to startup failure")
                except Exception:
                    logger.exception("Failed to close DB pool during startup cleanup")
            raise

    async def on_shutdown(self):
        logger.info("Bot shutdown initiated")
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Application Redis client closed")
            except Exception as e:
                logger.exception("Error closing Redis client: %s", e)
        if self.db_pool:
            try:
                await self.db_pool.close()
                logger.info("PostgreSQL pool closed")
            except Exception as e:
                logger.exception("Error closing DB pool: %s", e)
        if self.storage:
            try:
                await self.storage.close()
                logger.info("FSM storage closed")
            except Exception as e:
                logger.exception("Error closing FSM storage: %s", e)
        if self.bot:
            try:
                await self.bot.session.close()
                logger.info("Bot session closed")
            except Exception as e:
                logger.exception("Error closing bot session: %s", e)
        logger.info("Bot shutdown completed")

    async def run(self):
        try:
            await self.dp.start_polling(
                self.bot, allowed_updates=self.settings.ALLOWED_UPDATES
            )
        except Exception as e:
            logger.exception("Polling has failed: %s", e)

if __name__ == "__main__":
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    bot_app = BotApp(settings)
    try:
        asyncio.run(bot_app.run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Unexpected exception: %s", e)
        sys.exit(1)