import time
import asyncio
import logging

from fastapi import APIRouter, Depends, Response, status, HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.db.session import get_db
from app.cache.redis import redis
from celery import current_app as celery_app

router = APIRouter()
logger = logging.getLogger(__name__)

# Use monotonic for uptime measurement
start_time = time.monotonic()

# Metrics authentication
metrics_api_key_header = APIKeyHeader(name="X-Metrics-API-Key", auto_error=False)

async def metrics_auth(api_key: str = Security(metrics_api_key_header)):
    if not api_key or api_key != settings.METRICS_API_KEY:
        logger.warning("Unauthorized metrics access attempt")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return True

# Healthcheck timeouts (seconds)
TIMEOUT_DB = getattr(settings, 'HEALTHCHECK_TIMEOUT_DB', 2)
TIMEOUT_REDIS = getattr(settings, 'HEALTHCHECK_TIMEOUT_REDIS', 2)
TIMEOUT_CELERY = getattr(settings, 'HEALTHCHECK_TIMEOUT_CELERY', 2)

async def check_database(db: AsyncSession):
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=TIMEOUT_DB)
        return {'name': 'database', 'healthy': True}
    except asyncio.TimeoutError as e:
        return {'name': 'database', 'healthy': False, 'info': 'timeout', 'error': e}
    except Exception as e:
        return {'name': 'database', 'healthy': False, 'info': 'error', 'error': e}

async def check_redis():
    try:
        pong = await asyncio.wait_for(redis.ping(), timeout=TIMEOUT_REDIS)
        if pong:
            return {'name': 'redis', 'healthy': True}
        else:
            return {'name': 'redis', 'healthy': False, 'info': 'no response'}
    except asyncio.TimeoutError as e:
        return {'name': 'redis', 'healthy': False, 'info': 'timeout', 'error': e}
    except Exception as e:
        return {'name': 'redis', 'healthy': False, 'info': 'error', 'error': e}

async def check_celery():
    loop = asyncio.get_running_loop()
    try:
        inspect = celery_app.control.inspect(timeout=1)
        result = await asyncio.wait_for(loop.run_in_executor(None, inspect.ping), timeout=TIMEOUT_CELERY)
        if result:
            return {'name': 'celery', 'healthy': True}
        else:
            return {'name': 'celery', 'healthy': False, 'info': 'no workers'}
    except asyncio.TimeoutError as e:
        return {'name': 'celery', 'healthy': False, 'info': 'timeout', 'error': e}
    except Exception as e:
        return {'name': 'celery', 'healthy': False, 'info': 'error', 'error': e}

@router.get("/health", tags=["Health"], summary="Health Check")
async def healthcheck(db: AsyncSession = Depends(get_db)):
    checks = {}
    overall_ok = True

    results = await asyncio.gather(
        check_database(db),
        check_redis(),
        check_celery()
    )

    for result in results:
        name = result['name']
        healthy = result['healthy']
        info = result.get('info')
        error = result.get('error')

        if healthy:
            checks[name] = "ok"
        else:
            overall_ok = False
            if info in ('timeout', 'no workers', 'no response'):
                checks[name] = info
            else:
                checks[name] = "error"
            if error:
                logger.error(f"{name} health check failed", exc_info=error)

    status_code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if overall_ok else "error",
            "checks": checks,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": round(time.monotonic() - start_time, 2),
        },
    )

@router.get("/metrics", tags=["Metrics"], summary="Prometheus Metrics")
async def metrics_endpoint(_auth: bool = Depends(metrics_auth)):
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, generate_latest)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)