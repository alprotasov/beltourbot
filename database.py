import threading
import logging
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine: Optional[AsyncEngine] = None
_SessionMaker: Optional[sessionmaker] = None
_db_uri: Optional[str] = None
_db_echo: Optional[bool] = None
_init_lock = threading.Lock()

def init_db(uri: str, echo: bool = False) -> None:
    global _engine, _SessionMaker, _db_uri, _db_echo
    if _engine is not None:
        if uri != _db_uri or echo != _db_echo:
            logger.warning(
                "init_db called with different parameters. Existing uri=%s echo=%s, new uri=%s echo=%s. Ignoring new settings.",
                _db_uri, _db_echo, uri, echo
            )
        return
    with _init_lock:
        if _engine is not None:
            if uri != _db_uri or echo != _db_echo:
                logger.warning(
                    "init_db called with different parameters. Existing uri=%s echo=%s, new uri=%s echo=%s. Ignoring new settings.",
                    _db_uri, _db_echo, uri, echo
                )
            return
        _engine = create_async_engine(uri, echo=echo, future=True)
        _SessionMaker = sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
        _db_uri = uri
        _db_echo = echo

def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_db() first.")
    return _engine

def get_session() -> AsyncSession:
    if _SessionMaker is None:
        raise RuntimeError("Session maker is not initialized. Call init_db() first.")
    return _SessionMaker()

async def dispose_db() -> None:
    global _engine, _SessionMaker, _db_uri, _db_echo
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _SessionMaker = None
        _db_uri = None
        _db_echo = None

@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    session = get_session()
    try:
        yield session
        await session.commit()
    except:
        await session.rollback()
        raise
    finally:
        await session.close()