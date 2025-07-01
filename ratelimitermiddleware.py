import os
import logging
import redis.asyncio as redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

LOGGER = logging.getLogger(__name__)

def get_env_int(var_name: str, default: int) -> int:
    val = os.getenv(var_name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        LOGGER.warning(f"Invalid integer for {var_name}: {val}, using default {default}")
        return default

def get_env_list(var_name: str) -> list[str]:
    val = os.getenv(var_name, "")
    return [item.strip() for item in val.split(",") if item.strip()]

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT = get_env_int("RATE_LIMIT", 100)
RATE_LIMIT_WINDOW = get_env_int("RATE_LIMIT_WINDOW", 60)
TRUSTED_PROXIES = get_env_list("TRUSTED_PROXIES")

LUA_RATE_LIMIT_SCRIPT = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
    return {count, ARGV[1]}
else
    local ttl = redis.call("TTL", KEYS[1])
    return {count, ttl}
end
"""

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        self.limit = RATE_LIMIT
        self.window = RATE_LIMIT_WINDOW

    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)
        key = f"rl:{client_ip}"
        allowed, ttl = await self.check_rate_limit(key)
        if not allowed:
            LOGGER.warning(f"Rate limit exceeded for {client_ip}")
            retry_after = ttl if ttl > 0 else self.window
            return JSONResponse(
                {"detail": "Too Many Requests"},
                status_code=429,
                headers={"Retry-After": str(retry_after)}
            )
        response = await call_next(request)
        return response

    async def check_rate_limit(self, key: str) -> tuple[bool, int]:
        try:
            result = await self.redis.eval(LUA_RATE_LIMIT_SCRIPT, 1, key, self.window)
            if isinstance(result, list) and len(result) == 2:
                count = int(result[0])
                ttl = int(result[1])
            else:
                LOGGER.error(f"Unexpected LUA script result: {result}")
                return False, self.window
            if ttl <= 0:
                ttl = self.window
            allowed = count <= self.limit
            return allowed, ttl
        except Exception as e:
            LOGGER.error(f"Error checking rate limit for key {key}: {e}")
            return False, self.window

    @staticmethod
    def get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        client = request.client.host if request.client else None
        if forwarded and client and client in TRUSTED_PROXIES:
            return forwarded.split(",")[0].strip()
        if client:
            return client
        return "unknown"