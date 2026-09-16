from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.core.config.base import Environment
from fastapi_orderly.core.loggers import logger, setup_logging
from fastapi_orderly.routers import add_routers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    setup_logging(app)
    logger.info("Starting app lifespan")
    yield
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
