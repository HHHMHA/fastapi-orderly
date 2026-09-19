APP := fastapi_orderly
PYTHON := uv run python
UVX := uv run
ALEMBIC := uv run alembic

.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  make install       Install dependencies"
	@echo "  make dev           Run FastAPI locally"
	@echo "  make run           Run FastAPI with reload"
	@echo "  make test          Run tests"
	@echo "  make check         Run lint + tests"
	@echo "  make migrate       Apply migrations"
	@echo "  make migration     Create migration (msg='...')"
	@echo "  make downgrade     Roll back one migration"
	@echo "  make revision      Create empty migration (msg='...')"
	@echo "  make db            Open PostgreSQL shell"
	@echo "  make up            Start Docker services"
	@echo "  make down          Stop Docker services"
	@echo "  make logs          Follow Docker logs"
	@echo "  make build         Rebuild Docker images"
	@echo "  make shell         Open app container shell"
	@echo "  make clean         Remove caches"

install:
	uv sync

dev:
	$(UVX) uvicorn $(APP).main:create_app --reload --host 0.0.0.0 --port 8000 --factory

run:
	$(UVX) uvicorn $(APP).main:create_app --host 0.0.0.0 --port 8000 --factory

test:
	$(UVX) pytest

test-watch:
	$(UVX) pytest --watch

check:
	$(UVX) pre-commit run --all

# ── Database ──────────────────────────────────────────────

migrate:
	$(ALEMBIC) upgrade head

migration:
ifndef msg
	$(error msg is required. Example: make migration msg="create users")
endif
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

revision:
ifndef msg
	$(error msg is required. Example: make revision msg="add index")
endif
	$(ALEMBIC) revision -m "$(msg)"

downgrade:
	$(ALEMBIC) downgrade -1

history:
	$(ALEMBIC) history

current:
	$(ALEMBIC) current

stamp:
ifndef revision
	$(error revision is required. Example: make stamp revision=head)
endif
	$(ALEMBIC) stamp $(revision)

# ── Docker ────────────────────────────────────────────────

up:
	docker compose up -d

up-build:
	docker compose up -d --build

down:
	docker compose down

down-volumes:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

logs-app:
	docker compose logs -f app

logs-db:
	docker compose logs -f db

shell:
	docker compose exec app bash

db:
	docker compose exec db psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-app}

# Run migrations inside the Docker container
docker-migrate:
	docker compose exec app alembic upgrade head

docker-migration:
ifndef msg
	$(error msg is required. Example: make docker-migration msg="create users")
endif
	docker compose exec app alembic revision --autogenerate -m "$(msg)"

# ── Cleanup ───────────────────────────────────────────────

clean:
	find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".ruff_cache" \) -prune -exec rm -rf {} +
	rm -rf .coverage htmlcov

clean-all: clean
	rm -rf .venv
