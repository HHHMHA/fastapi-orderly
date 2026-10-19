from unittest.mock import MagicMock

from fastapi import Request
from redis.asyncio import Redis

from fastapi_orderly.core.redis_con import get_redis


def test_get_redis() -> None:
    redis_mock = MagicMock(spec=Redis)
    request = MagicMock(spec=Request)
    request.state.redis = redis_mock

    result = get_redis(request)

    assert result is redis_mock
