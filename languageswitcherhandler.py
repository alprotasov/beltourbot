import logging
from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.utils.callback_data import CallbackData
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from loader import dp, _
from database import async_session
from models.user import User
from core.redis import redis_client
from settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

LANGUAGE_CACHE_TTL = 86400  # seconds

language_cb = CallbackData("lang_switch", "lang_code")

async def get_user_language(user_id: int) -> str:
    key = f"user:{user_id}:lang"
    # Try fetching from cache
    try:
        cached = await redis_client.get(key)
        if cached:
            return cached.decode("utf-8")
    except Exception as e:
        logger.warning("Redis get error for user %s: %s", user_id, e)
    # Fetch from database
    try:
        async with async_session() as session:
            result = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = result.scalars().first()
            if user:
                if user.language in SUPPORTED_LANGUAGES:
                    lang = user.language
                else:
                    # Unsupported language: reset to default
                    lang = DEFAULT_LANGUAGE
                    user.language = lang
                    await session.commit()
            else:
                lang = DEFAULT_LANGUAGE
                user = User(telegram_id=user_id, language=lang)
                session.add(user)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    # Race condition: fetch the user inserted by another process
                    result = await session.execute(select(User).filter_by(telegram_id=user_id))
                    user = result.scalars().first()
            # Cache the result
            try:
                await redis_client.set(key, lang, ex=LANGUAGE_CACHE_TTL)
            except Exception as e:
                logger.warning("Redis set error for user %s: %s", user_id, e)
            return lang
    except SQLAlchemyError as e:
        logger.exception("DB error fetching language for user %s: %s", user_id, e)
        return DEFAULT_LANGUAGE

async def set_user_language(user_id: int, lang: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {lang}")
    key = f"user:{user_id}:lang"
    # Update database
    try:
        async with async_session() as session:
            result = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = result.scalars().first()
            if user:
                user.language = lang
            else:
                user = User(telegram_id=user_id, language=lang)
                session.add(user)
            await session.commit()
    except SQLAlchemyError as e:
        logger.exception("DB error setting language for user %s: %s", user_id, e)
        raise
    # Update cache
    try:
        await redis_client.set(key, lang, ex=LANGUAGE_CACHE_TTL)
    except Exception as e:
        logger.warning("Redis set error for user %s: %s", user_id, e)

@dp.message_handler(Command(["language", "lang"]))
async def handle_language_switch(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for code, name in SUPPORTED_LANGUAGES.items():
        keyboard.insert(
            types.InlineKeyboardButton(
                text=name,
                callback_data=language_cb.new(lang_code=code)
            )
        )
    await message.answer(_("choose_language"), reply_markup=keyboard)

@dp.callback_query_handler(language_cb.filter())
async def process_language_change(callback_query: types.CallbackQuery, callback_data: dict):
    lang = callback_data.get("lang_code")
    user_id = callback_query.from_user.id
    try:
        await set_user_language(user_id, lang)
        await callback_query.answer(_("language_changed"), show_alert=True)
        await callback_query.message.edit_reply_markup()
    except ValueError as e:
        await callback_query.answer(str(e), show_alert=True)
    except Exception:
        await callback_query.answer(_("error_occurred"), show_alert=True)