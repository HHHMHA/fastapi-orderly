from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from fastapi_orderly.main import lifespan


@pytest.mark.asyncio
async def test_lifespan() -> None:
    app = FastAPI()
    db = MagicMock()
    db.dispose = AsyncMock()

    redis = MagicMock()
    redis.aclose = AsyncMock()
    redis.ping = AsyncMock()

    with (
        patch("fastapi_orderly.main.setup_logging") as setup_logging,
        patch("fastapi_orderly.main.setup_redis", return_value=redis) as setup_redis,
        patch("fastapi_orderly.main.Database", return_value=db) as Database,  # noqa: N806
        patch("fastapi_orderly.main.get_settings") as get_settings,
    ):
        async with lifespan(app) as state:
            setup_logging.assert_called_once_with(app)
            setup_redis.assert_called_once_with(get_settings.return_value)
            get_settings.assert_called_once_with()
            Database.assert_called_once_with(get_settings.return_value)

            assert state == {"database": db, "redis": redis}
            db.dispose.assert_not_awaited()
            redis.aclose.assert_not_awaited()
            redis.ping.assert_awaited_once()

        db.dispose.assert_awaited_once()
        redis.aclose.assert_awaited_once()
