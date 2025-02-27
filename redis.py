import aioredis

from typing import Optional


class RedisUtils(object):
    def __init__(self, redis_url: str,
                 password: Optional[str] = None,
                 decode_responses: Optional[bool] = True,
                 **kwargs):
        self.redis_url = redis_url
        self.redis_kwargs = dict(
            password=password,
            decode_responses=decode_responses,
            **kwargs)
        self.redis = None

    async def connect(self):
        self.redis = await aioredis.from_url(self.redis_url, **self.redis_kwargs)

    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            self.redis = None

    def __getattribute__(self, func):
        return getattr(self.redis, func)
