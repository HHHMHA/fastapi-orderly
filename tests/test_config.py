import pytest
from pydantic import ValidationError

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.core.config.base import Settings


def test_settings_reads_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "true")

    settings = get_settings()

    assert settings.debug is True


def test_settings_requires_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(
            debug=False,
            app_name="orderly",
        )


def test_settings_rejects_invalid_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "invalid")

    with pytest.raises(ValidationError):
        get_settings()
