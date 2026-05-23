import logging
from typing import Optional
import redis.asyncio as aioredis
from backend.app.config import settings

logger = logging.getLogger("neuralpulse.redis")


class RedisClient:
    _instance: Optional["RedisClient"] = None
    client: Optional[aioredis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        try:
            self.client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                encoding="utf-8"
            )
            await self.client.ping()
            logger.info("Connected to Redis server successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis server: {e}")
            raise e

    async def disconnect(self) -> None:
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis server")

    async def get(self, key: str) -> Optional[str]:
        if not self.client:
            return None
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        if not self.client:
            return False
        return await self.client.set(key, value, ex=ex)

    async def delete(self, key: str) -> int:
        if not self.client:
            return 0
        return await self.client.delete(key)

    async def publish(self, channel: str, message: str) -> int:
        if not self.client:
            return 0
        return await self.client.publish(channel, message)


redis_client = RedisClient()
