from collections.abc import Generator

import pytest

from fastapi_orderly.core.config import get_settings


@pytest.fixture(autouse=True)
def required_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("APP_NAME", "orderly")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ENV_FILE", ".env.test")


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
