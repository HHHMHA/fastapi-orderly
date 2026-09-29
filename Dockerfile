FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

# Runtime
FROM python:3.13-slim-bookworm AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH"

USER appuser

WORKDIR /app

# Development
FROM base AS dev

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    uv sync --locked

CMD ["uvicorn", "fastapi_orderly.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--factory"]


# Production
FROM base AS prod

CMD ["uvicorn", "fastapi_orderly.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
