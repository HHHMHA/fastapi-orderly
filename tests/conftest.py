import asyncio
import sys
from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncTransaction

from fastapi_orderly.core.config import Settings, get_settings
from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.core.db.session import Database, get_session
from fastapi_orderly.core.redis_con import get_redis, setup_redis
from fastapi_orderly.main import create_app
from fastapi_orderly.modules.auth.deps import get_user_repository, get_user_service
from fastapi_orderly.modules.auth.hasher import get_hasher
from fastapi_orderly.modules.auth.services import UserService
from fastapi_orderly.modules.notifications.channels.options import ChannelOptions, ChannelType
from fastapi_orderly.modules.notifications.notification_type import NotificationType
from fastapi_orderly.modules.notifications.services import NotificationService
from fastapi_orderly.modules.otp.deps import get_otp_repository, get_otp_service
from fastapi_orderly.modules.otp.services import OTPService
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
async def user(no_app_db_session: AsyncSession) -> UserAccount:
    user = UserAccount(
        username="test",
        email="test@example.com",
        password="test",
    )
    no_app_db_session.add(user)
    await no_app_db_session.flush()
    return user


class FakeNotificationChannel:
    def __init__(self) -> None:
        self.calls: list[tuple[NotificationType, ChannelOptions]] = []

    async def send(
        self,
        notification_type: NotificationType,
        options: ChannelOptions,
    ) -> None:
        self.calls.append((notification_type, options))


@pytest.fixture
def notification_service() -> NotificationService:
    email_channel = FakeNotificationChannel()

    service = NotificationService(
        channels={
            ChannelType.EMAIL: email_channel,
        }
    )
    return service


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis]:
    redis = setup_redis(get_settings())

    try:
        await redis.flushdb()
        yield redis
    finally:
        await redis.flushdb()
        await redis.aclose()


@pytest.fixture
def otp_service(
    no_app_db_session: AsyncSession,
    notification_service: NotificationService,
    redis_client: Redis,
) -> OTPService:
    return get_otp_service(
        get_otp_repository(session=no_app_db_session),
        hasher=FakeHasher(),
        settings=get_settings(),
        notification_service=notification_service,
        redis=redis_client,
    )


@pytest.fixture
def user_service(
    no_app_db_session: AsyncSession,
    otp_service: OTPService,
) -> UserService:
    return get_user_service(
        user_repository=get_user_repository(session=no_app_db_session),
        hasher=FakeHasher(),
        otp_service=otp_service,
    )


@pytest_asyncio.fixture
async def client(
    no_app_db_session: AsyncSession, redis_client: Redis
) -> AsyncGenerator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_hasher] = lambda: FakeHasher()
    app.dependency_overrides[get_redis] = lambda: redis_client

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield no_app_db_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
