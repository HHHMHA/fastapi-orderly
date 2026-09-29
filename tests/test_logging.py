import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from fastapi_orderly.core.config import Environment
from fastapi_orderly.core.loggers import (
    JSONFormatter,
    configure_logging,
    setup_logging,
)


class TestJSONFormatter:
    def test_formats_basic_record(self) -> None:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Hello %s",
            args=("world",),
            exc_info=None,
        )

        result = json.loads(formatter.format(record))

        assert result == {
            "timestamp": result["timestamp"],
            "level": "INFO",
            "logger": "app",
            "message": "Hello world",
            "taskName": None,
        }

    def test_includes_exception(self) -> None:
        formatter = JSONFormatter()

        try:
            raise ValueError("something went wrong")
        except ValueError:
            record = logging.LogRecord(
                name="app",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Request failed",
                args=(),
                exc_info=__import__("sys").exc_info(),
            )

        result = json.loads(formatter.format(record))

        assert result["level"] == "ERROR"
        assert result["message"] == "Request failed"
        assert result["exception"]["type"] == "ValueError"
        assert result["exception"]["message"] == "something went wrong"
        assert "ValueError: something went wrong" in result["exception"]["traceback"]

    def test_includes_serializable_extra_fields(self) -> None:
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc123"
        record.status_code = 200
        record.metadata = {"foo": "bar"}

        result = json.loads(formatter.format(record))

        assert result["request_id"] == "abc123"
        assert result["status_code"] == 200
        assert result["metadata"] == {"foo": "bar"}

    def test_converts_non_serializable_extra_fields_to_string(self) -> None:
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request",
            args=(),
            exc_info=None,
        )
        record.custom = object()

        result = json.loads(formatter.format(record))

        assert result["custom"] == str(record.custom)

    def test_does_not_include_reserved_fields(self) -> None:
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request",
            args=(),
            exc_info=None,
        )

        result = json.loads(formatter.format(record))

        assert "pathname" not in result
        assert "lineno" not in result
        assert "funcName" not in result
        assert "levelno" not in result


@pytest.mark.parametrize(
    ("environment", "expected_formatter"),
    [
        (Environment.LOCAL, logging.Formatter),
        (Environment.TEST, JSONFormatter),
        (Environment.STAGING, JSONFormatter),
        (Environment.PRODUCTION, JSONFormatter),
    ],
)
def test_configure_logging(
    environment: Environment, expected_formatter: type[logging.Formatter]
) -> None:
    mock_settings = MagicMock()
    mock_settings.log_level = logging.INFO
    mock_settings.environment = environment

    root = logging.getLogger()
    old_handlers = root.handlers.copy()

    try:
        with patch(
            "fastapi_orderly.core.loggers.get_settings",
            return_value=mock_settings,
        ):
            configure_logging()

            assert root.level == logging.INFO
            assert len(root.handlers) == 1

            handler = root.handlers[0]

            assert handler.level == logging.INFO
            assert isinstance(handler, logging.StreamHandler)
            assert isinstance(handler.formatter, expected_formatter)

            assert logging.getLogger("app").level == logging.INFO
            assert logging.getLogger("httpx").level == logging.WARNING
            assert logging.getLogger("httpcore").level == logging.WARNING
            assert logging.getLogger("multipart").level == logging.WARNING

            for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
                logger = logging.getLogger(name)
                assert logger.handlers == []
                assert logger.propagate is True
    finally:
        root.handlers.clear()
        root.handlers.extend(old_handlers)


def test_setup_logging() -> None:
    app = MagicMock()

    with patch("fastapi_orderly.core.loggers.configure_logging") as configure:
        setup_logging(app)

        configure.assert_called_once_with()
