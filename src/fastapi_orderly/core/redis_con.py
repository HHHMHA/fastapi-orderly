from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis, from_url

from fastapi_orderly.core.config import Settings


def setup_redis(settings: Settings) -> Redis:
    return from_url(
        str(settings.redis.url),
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.redis.max_connections,
        socket_connect_timeout=settings.redis.socket_connect_timeout,
        socket_timeout=settings.redis.socket_timeout,
        health_check_interval=settings.redis.health_check_interval,
    )


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.state.redis)


RedisDep = Annotated[Redis, Depends(get_redis)]
