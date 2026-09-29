from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.core.config.base import Environment
from fastapi_orderly.core.db.session import Database
from fastapi_orderly.core.loggers import logger, setup_logging
from fastapi_orderly.routers import add_routers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict[str, Any]]:
    setup_logging(app)
    database = Database(get_settings())
    logger.info("Starting app lifespan")

    yield {"database": database}

    await database.dispose()
    logger.info("Exiting app lifespan")


def create_app() -> FastAPI:
    settings = get_settings()  # TODO: override from db managed settings
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version=settings.version,
        docs_url=None if settings.environment == Environment.PRODUCTION else "/docs",
        redoc_url=None if settings.environment == Environment.PRODUCTION else "/redoc",
        openapi_url=None if settings.environment == Environment.PRODUCTION else "/openapi.json",
        lifespan=lifespan,
    )
    add_routers(app)
    return app
