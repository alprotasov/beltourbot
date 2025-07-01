import logging
import uuid
from redis.asyncio import Redis
from redis.asyncio.exceptions import RedisError

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter using Redis sorted sets and Lua script for atomic operations.
    """

    _lua_script = """
local key = KEYS[1]
local window_ms = tonumber(ARGV[1]) * 1000
local max_requests = tonumber(ARGV[2])
local member = ARGV[3]
local time = redis.call('TIME')
local now_sec = tonumber(time[1])
local now_usec = tonumber(time[2])
local now_ms = now_sec * 1000 + math.floor(now_usec / 1000)
redis.call('ZREMRANGEBYSCORE', key, 0, now_ms - window_ms)
local count = redis.call('ZCARD', key)
if count < max_requests then
    redis.call('ZADD', key, now_ms, member)
    redis.call('PEXPIRE', key, window_ms)
    return 1
else
    return 0
end
"""

    def __init__(self, redis_client: Redis, max_requests: int, window_seconds: int, prefix: str = "rl"):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix

    def _key(self, identifier: str) -> str:
        return f"{self.prefix}:{identifier}"

    async def attempt(self, identifier: str) -> bool:
        key = self._key(identifier)
        member = uuid.uuid4().hex
        try:
            result = await self.redis.eval(self._lua_script, 1, key, self.window_seconds, self.max_requests, member)
            return bool(result)
        except RedisError as e:
            logger.error("Redis error during rate limiting attempt for %s: %s", identifier, e)
            return True