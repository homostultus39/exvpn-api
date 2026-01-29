from typing import Optional

import redis.asyncio as aioredis

from src.redis.connection import get_redis


class RedisClient:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def save_access_token(self, user_id: str, token: str, expires_in: int) -> None:
        key = f"access_token:{user_id}:{token}"
        await self.redis.setex(key, expires_in, "1")

    async def get_access_token(self, user_id: str, token: str) -> Optional[str]:
        key = f"access_token:{user_id}:{token}"
        result = await self.redis.get(key)
        return result if result else None

    async def delete_access_token(self, user_id: str, token: str) -> None:
        key = f"access_token:{user_id}:{token}"
        await self.redis.delete(key)

    async def save_refresh_token(self, user_id: str, token: str, expires_in: int) -> None:
        key = f"refresh_token:{user_id}:{token}"
        await self.redis.setex(key, expires_in, "1")

    async def get_refresh_token(self, user_id: str, token: str) -> Optional[str]:
        key = f"refresh_token:{user_id}:{token}"
        result = await self.redis.get(key)
        return result if result else None

    async def delete_refresh_token(self, user_id: str, token: str) -> None:
        key = f"refresh_token:{user_id}:{token}"
        await self.redis.delete(key)

    async def delete_all_user_tokens(self, user_id: str) -> None:
        pattern = f"access_token:{user_id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

        pattern = f"refresh_token:{user_id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break


async def get_redis_client() -> RedisClient:
    redis = await get_redis()
    return RedisClient(redis)
