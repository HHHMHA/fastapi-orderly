# logging.py

from __future__ import annotations

import logging

# import logging.config
import sys

# import time
# from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI

from fastapi_orderly.core.config import Environment, get_settings


class JSONFormatter(logging.Formatter):
    """
    Structured JSON formatter suitable for production log aggregation.

    Outputs one JSON object per log line.
    """

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Include structured fields passed with `extra={...}`.
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
        }

        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                try:
                    json.dumps(value)
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = str(value)

        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )


def configure_logging() -> None:
    settings = get_settings()
    level = settings.log_level

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    if settings.environment != Environment.LOCAL:
        formatter = JSONFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)

    # Application logs.
    logging.getLogger("app").setLevel(level)

    # Uvicorn logs.
    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
    ):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True

    # Prevent overly noisy third-party libraries.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)


logger = logging.getLogger("app")


# class RequestLoggingMiddleware(BaseHTTPMiddleware):
#     """
#     Logs every HTTP request with:

#         request_id
#         method
#         path
#         status_code
#         duration_ms
#         client_ip
#     """

#     async def dispatch(
#         self,
#         request: Request,
#         call_next: Callable[[Request], Awaitable[Response]],
#     ) -> Response:
#         # request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

#         # token = _request_id.set(request_id)
#         # request.state.request_id = request_id

#         started = time.perf_counter()

#         try:
#             response = await call_next(request)

#             duration_ms = round(
#                 (time.perf_counter() - started) * 1000,
#                 2,
#             )

#             client_ip = request.client.host if request.client else None

#             logger.info(
#                 "HTTP request",
#                 extra={
#                     "http": {
#                         "method": request.method,
#                         "path": request.url.path,
#                         "query": request.url.query or None,
#                         "status_code": response.status_code,
#                         "duration_ms": duration_ms,
#                     },
#                     "client": {
#                         "ip": client_ip,
#                     },
#                 },
#             )

#             # response.headers["X-Request-ID"] = request_id

#             return response

#         except Exception:
#             duration_ms = round(
#                 (time.perf_counter() - started) * 1000,
#                 2,
#             )

#             client_ip = request.client.host if request.client else None

#             logger.exception(
#                 "Unhandled exception while processing HTTP request",
#                 extra={
#                     "http": {
#                         "method": request.method,
#                         "path": request.url.path,
#                         "query": request.url.query or None,
#                         "duration_ms": duration_ms,
#                     },
#                     "client": {
#                         "ip": client_ip,
#                     },
#                 },
#             )

#             raise

#         finally:
#             pass
#             # _request_id.reset(token)


def setup_logging(app: FastAPI) -> None:
    """
    Configure logging and attach request logging middleware.

    Call once during application startup.
    """

    configure_logging()
