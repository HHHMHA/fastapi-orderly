from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from fastapi_orderly.main import lifespan


@pytest.mark.asyncio
async def test_lifespan() -> None:
    app = FastAPI()
    db = MagicMock()
    db.dispose = AsyncMock()

    with (
        patch("fastapi_orderly.main.setup_logging") as setup_logging,
        patch("fastapi_orderly.main.Database", return_value=db) as Database,  # noqa: N806
        patch("fastapi_orderly.main.get_settings") as get_settings,
    ):
        async with lifespan(app) as state:
            setup_logging.assert_called_once_with(app)
            get_settings.assert_called_once_with()
            Database.assert_called_once_with(get_settings.return_value)

            assert state == {"database": db}
            db.dispose.assert_not_awaited()

        db.dispose.assert_awaited_once()
