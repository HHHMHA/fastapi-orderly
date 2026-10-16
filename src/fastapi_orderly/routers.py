from fastapi import FastAPI

from fastapi_orderly.modules.auth.endpoints import auth_router
from fastapi_orderly.modules.health.endpoints import health_router


def add_routers(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/v1")
