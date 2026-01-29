import redis.asyncio as aioredis

from src.utils.settings import get_settings

settings = get_settings()

redis_pool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=10
)


async def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)
