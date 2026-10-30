from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any, TypeVar, cast

from sqlalchemy import (
    ColumnElement,
    CursorResult,
    UnaryExpression,
    delete,
    func,
    insert,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import Select

from fastapi_orderly.core.db.base import ActivatableBase, Base

OrderByT = TypeVar(
    "OrderByT",
    str,
    ColumnElement[object],
    UnaryExpression[str],
    InstrumentedAttribute[str],
)


class RepositoryBase[T: Base]:
    Model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session: AsyncSession = session

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

        if not getattr(cls, "__abstract__", False) and "Model" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define Model")

    def get_base_query(
        self, *where: ColumnElement[bool], order_by: OrderByT | None = None
    ) -> Select[tuple[T]]:
        return select(self.Model).where(*where).order_by(order_by)

    async def run(
        self,
        statement: Select[tuple[T]],
    ) -> list[T]:
        result = await self.session.scalars(statement)
        return list(result.all())

    async def stream(
        self,
        *where: ColumnElement[bool],
        batch_size: int = 1_000,
        order_by: OrderByT | None = None,
    ) -> AsyncIterator[T]:
        stmt = self.get_base_query(*where, order_by=order_by).execution_options(
            yield_per=batch_size
        )

        result = await self.session.stream_scalars(stmt)

        async for item in result:
            yield item

    async def filter(
        self,
        *where: ColumnElement[bool],
        limit: int | None = None,
        offset: int | None = None,
        order_by: OrderByT | None = None,
    ) -> list[T]:
        stmt = self.get_base_query(*where, order_by=order_by).limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def first(
        self,
        *where: ColumnElement[bool],
        order_by: OrderByT | None = None,
    ) -> T | None:
        result: list[T] = await self.filter(
            *where,
            limit=1,
            order_by=order_by,
        )
        return result[0] if result else None

    async def count(
        self,
        *where: ColumnElement[bool],
    ) -> int:
        stmt = select(func.count()).select_from(self.get_base_query(*where).subquery())
        return await self.session.scalar(stmt) or 0

    async def page(
        self,
        *where: ColumnElement[bool],
        page: int = 1,
        page_size: int = 100,
        order_by: OrderByT | None = None,
    ) -> tuple[list[T], int]:
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")

        offset = (page - 1) * page_size

        items = await self.filter(
            *where,
            limit=page_size,
            offset=offset,
            order_by=order_by,
        )
        total = await self.count(*where)

        return items, total

    async def all(self, order_by: OrderByT | None = None) -> list[T]:
        return await self.filter(order_by=order_by)

    async def get(self, ident: object) -> T | None:
        return await self.session.get(self.Model, ident)

    async def get_or_else(
        self,
        *where: ColumnElement[bool],
        handler: Callable[[], T | None],
    ) -> T | None:
        result = await self.first(*where)
        return result if result is not None else handler()

    async def get_or_merge(
        self,
        *where: ColumnElement[bool],
        handler: Callable[[], T | None],
        exclude: tuple[InstrumentedAttribute[object], ...] = (),
    ) -> T | None:
        existing = await self.first(*where)
        incoming = handler()

        if incoming is None:
            return existing

        if existing is None:
            self.session.add(incoming)
            return incoming

        excluded = {column.key for column in exclude}

        for key, value in vars(incoming).items():
            if not key.startswith("_") and key not in excluded:
                setattr(existing, key, value)

        return existing

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, ident: object) -> bool:
        entity = await self.get(ident)
        if entity is None:
            return False

        await self.delete(entity)
        await self.session.flush()
        return True

    async def save(self, entity: T) -> None:
        self.session.add(entity)
        await self.session.flush()

    async def bulk_insert(self, entities: Sequence[T]) -> None:
        if not entities:
            return

        await self.session.execute(
            insert(self.Model),
            [
                {key: value for key, value in vars(entity).items() if not key.startswith("_")}
                for entity in entities
            ],
        )
        await self.session.flush()

    async def exists(
        self,
        *where: ColumnElement[bool],
    ) -> bool:
        stmt = self.get_base_query(*where).exists()
        return bool(await self.session.scalar(select(stmt)))

    async def get_existing_fields(
        self,
        **where: ColumnElement[bool],
    ) -> set[str]:
        if not where:
            return set()

        stmt = (
            select(*(condition.label(name) for name, condition in where.items()))
            .select_from(self.Model)
            .where(or_(*where.values()))
        )

        result = await self.session.execute(stmt)
        row = result.one_or_none()

        if not row:
            return set()

        return {name for name, exists in zip(where, row or (), strict=True) if exists}

    async def delete_where(
        self,
        *where: ColumnElement[bool],
    ) -> int:
        statement = delete(self.Model).where(*where)

        result = cast(
            CursorResult[Any],
            await self.session.execute(statement),
        )

        await self.session.flush()

        return result.rowcount


class ActivatorRepositoryMixin[T: ActivatableBase](RepositoryBase[T]):
    __abstract__ = True

    def filter_is_active(self) -> Select[tuple[T]]:
        return self.get_base_query(self.Model.is_active.is_(True))

    def filter_is_disabled(self) -> Select[tuple[T]]:
        return self.get_base_query(self.Model.is_active.is_(False))
