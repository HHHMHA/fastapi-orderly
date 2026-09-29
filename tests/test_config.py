import pytest
from pydantic import ValidationError
from pydantic.types import SecretStr

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
        Settings(  # pyright: ignore[reportCallIssue]
            debug=False,
            app_name="orderly",
        )


def test_settings_rejects_invalid_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "invalid")

    with pytest.raises(ValidationError):
        get_settings()


def test_database_settings_url() -> None:
    settings = get_settings()
    database = settings.db

    assert database.url.render_as_string(hide_password=False) == (
        f"{database.driver}://"
        f"{database.user}:{database.password.get_secret_value()}"
        f"@{database.host}:{database.port}/{database.name}"
    )

    database.password = SecretStr("p@ss:w/ord")
    assert database.url.render_as_string(hide_password=False) == (
        f"{database.driver}://"
        f"{database.user}:p%40ss%3Aw%2Ford"
        f"@{database.host}:{database.port}/{database.name}"
    )
