import logging
import asyncio
from fastapi import APIRouter, status
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy import text
from database import engine as async_engine
from bot import redis_client
from celery_worker import celery_app

router = APIRouter()

DB_TIMEOUT = 5
REDIS_TIMEOUT = 2
CELERY_TIMEOUT = 5

@router.get("/healthcheck", include_in_schema=False)
async def healthcheck():
    return JSONResponse({"status": "ok"})

@router.get("/readiness", include_in_schema=False)
async def readiness():
    errors = {}

    # Database readiness check
    try:
        async def _db_check():
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        await asyncio.wait_for(_db_check(), timeout=DB_TIMEOUT)
    except asyncio.TimeoutError:
        logging.exception("Database readiness check timed out")
        errors["database"] = "timeout"
    except Exception:
        logging.exception("Database readiness check failed")
        errors["database"] = "unavailable"

    # Redis readiness check
    try:
        await asyncio.wait_for(redis_client.ping(), timeout=REDIS_TIMEOUT)
    except asyncio.TimeoutError:
        logging.exception("Redis readiness check timed out")
        errors["redis"] = "timeout"
    except Exception:
        logging.exception("Redis readiness check failed")
        errors["redis"] = "unavailable"

    # Celery readiness check
    try:
        def _check_celery():
            response = celery_app.control.inspect(timeout=1).ping()
            if not response:
                raise RuntimeError("No running Celery workers")
        await asyncio.wait_for(run_in_threadpool(_check_celery), timeout=CELERY_TIMEOUT)
    except asyncio.TimeoutError:
        logging.exception("Celery readiness check timed out")
        errors["celery"] = "timeout"
    except Exception:
        logging.exception("Celery readiness check failed")
        errors["celery"] = "unavailable"

    if errors:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unready", "errors": errors},
        )

    return JSONResponse({"status": "ready"})