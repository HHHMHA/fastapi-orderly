import os
from functools import lru_cache

from fastapi_orderly.core.config.base import Environment, Settings


@lru_cache
def get_settings() -> Settings:
    env_file = os.getenv("ENV_FILE", ".env")
    settings: Settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    return settings


__all__ = ["Environment", "Settings", "get_settings"]
