import asyncio
import sys
from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncTransaction

from fastapi_orderly.core.config import Settings, get_settings
from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.core.db.session import Database
from fastapi_orderly.main import create_app
from fastapi_orderly.modules.auth.hasher import get_hasher
from tests.utils import FakeHasher


def pytest_configure() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # pyright: ignore[reportDeprecated]


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    settings: Settings = get_settings()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.db.url.render_as_string(hide_password=False))
    return config


@pytest_asyncio.fixture(scope="session")
async def no_app_db(alembic_config: Config) -> AsyncGenerator[Database]:
    settings: Settings = get_settings()
    database = Database(settings=settings)

    # Upgrade
    await asyncio.to_thread(
        command.upgrade,
        alembic_config,
        "head",
    )

    # async with database.engine.begin() as connection:
    #     await connection.run_sync(database.Base.metadata.create_all)

    yield database

    # async with database.engine.begin() as connection:
    #     await connection.run_sync(database.Base.metadata.drop_all)

    # Downgrade
    await asyncio.to_thread(
        command.downgrade,
        alembic_config,
        "base",
    )

    await database.dispose()


# @pytest.fixture
# def no_app_db_session(no_app_db: Database) -> Generator[Session]:
#     with no_app_db.session_factory() as session:
#         yield session
#         session.rollback()


@pytest_asyncio.fixture
async def no_app_db_session(
    no_app_db: Database,
) -> AsyncGenerator[AsyncSession]:
    async with no_app_db.engine.connect() as connection:
        transaction: AsyncTransaction = await connection.begin()

        session: AsyncSession = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture()
def fake_request() -> Request:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )
    return request


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_hasher] = FakeHasher

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(no_app_db_session: AsyncSession) -> UserAccount:
    user = UserAccount(
        username="test",
        email="test@example.com",
        password="test",
    )
    no_app_db_session.add(user)
    await no_app_db_session.flush()
    return user
