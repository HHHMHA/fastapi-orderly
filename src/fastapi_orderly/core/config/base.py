from enum import StrEnum
from importlib.metadata import version

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "prod"


class LogLevel(StrEnum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_file_encoding="utf-8", extra="ignore"
    )
    environment: Environment = Environment.LOCAL
    debug: bool
    app_name: str = "orderly"
    secret_key: SecretStr
    log_level: LogLevel = LogLevel.INFO
    version: str = version("fastapi-orderly")
