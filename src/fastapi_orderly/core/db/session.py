from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fastapi_orderly.core.config import Settings
from fastapi_orderly.core.db.base import Base


class Database:
    def __init__(self, settings: Settings) -> None:
        # Can use make_url instead and pass settings.db.url()

        self.engine: AsyncEngine = create_async_engine(
            settings.db.url,
            echo=settings.debug,
            pool_pre_ping=True,
        )

        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.Base = Base

    async def dispose(self) -> None:
        await self.engine.dispose()


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    database: Database = request.state.database

    async with database.session_factory() as session:
        yield session
