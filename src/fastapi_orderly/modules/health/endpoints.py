from typing import Annotated

from fastapi import APIRouter, Depends

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.core.config.base import Settings
from fastapi_orderly.modules.health.dtos import HealthResponse

health_router = APIRouter()


@health_router.get(path="/health", tags=["health"])
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.version)  # TODO: make actual checks
