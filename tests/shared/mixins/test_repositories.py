import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.modules.auth.models import UserAccount
from fastapi_orderly.shared.mixins.reposotories import RepositoryBase


class FakeUserRepository(RepositoryBase[UserAccount]):
    Model: type[UserAccount] = UserAccount


class TestBaseRepository:
    def test_model_required(self) -> None:
        with pytest.raises(TypeError):

            class FakeRepository(RepositoryBase[UserAccount]):
                pass

    async def test_get(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        user = await repo.get(1)
        assert user is None

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert user.id is not None

        user = await repo.get(user.id)

        assert user is not None
        assert user.username == "test"
        assert user.password == "test"
        assert user.email == "test@example.com"
        assert user.is_active
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_all(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        users = await repo.all()
        assert users == []

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        users = await repo.all()

        assert users == [user]

    async def test_filter(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        users = [
            UserAccount(
                username=f"user{i}",
                password="test",
                email=f"user{i}@example.com",
            )
            for i in range(3)
        ]
        for user in users:
            await repo.save(user)

        await no_app_db_session.commit()

        result = await repo.filter(UserAccount.username == "user1")

        assert result == [users[1]]

        result = await repo.filter(order_by=UserAccount.username.desc())

        assert result[0] == users[2]

    async def test_filter_limit_and_offset(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        users = [
            UserAccount(
                username=f"user{i}",
                password="test",
                email=f"user{i}@example.com",
            )
            for i in range(5)
        ]
        for user in users:
            await repo.save(user)

        await no_app_db_session.commit()

        result = await repo.filter(
            limit=2,
            offset=1,
        )

        assert len(result) == 2

    async def test_count(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        assert await repo.count() == 0

        users = [
            UserAccount(
                username=f"user{i}",
                password="test",
                email=f"user{i}@example.com",
            )
            for i in range(3)
        ]
        for user in users:
            await repo.save(user)

        await no_app_db_session.commit()

        assert await repo.count() == 3
        assert await repo.count(UserAccount.username == "user1") == 1

    async def test_page(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        users = [
            UserAccount(
                username=f"user{i}",
                password="test",
                email=f"user{i}@example.com",
            )
            for i in range(5)
        ]
        for user in users:
            await repo.save(user)

        await no_app_db_session.commit()

        items, total = await repo.page(
            page=1,
            page_size=2,
        )

        assert len(items) == 2
        assert total == 5

        items, total = await repo.page(
            page=2,
            page_size=2,
        )

        assert len(items) == 2
        assert total == 5

        items, total = await repo.page(
            page=3,
            page_size=2,
        )

        assert len(items) == 1
        assert total == 5

    @pytest.mark.parametrize(
        ("page", "page_size"),
        [
            (0, 1),
            (-1, 1),
            (1, 0),
            (1, -1),
            (0, 0),
        ],
    )
    async def test_page_rejects_invalid_pagination(
        self,
        no_app_db_session: AsyncSession,
        page: int,
        page_size: int,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        with pytest.raises(ValueError):
            await repo.page(
                page=page,
                page_size=page_size,
            )

    async def test_stream(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        users = [
            UserAccount(
                username=f"user{i}",
                password="test",
                email=f"user{i}@example.com",
            )
            for i in range(3)
        ]
        for user in users:
            await repo.save(user)

        await no_app_db_session.commit()

        result = [user async for user in repo.stream()]

        assert result == users

    async def test_stream_with_filter(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        users = [
            UserAccount(
                username=f"user{i}",
                password="test",
                email=f"user{i}@example.com",
            )
            for i in range(3)
        ]
        for user in users:
            await repo.save(user)

        await no_app_db_session.commit()

        result = [
            user
            async for user in repo.stream(
                UserAccount.username == "user1",
            )
        ]

        assert result == [users[1]]

    async def test_delete(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        await repo.delete(user)
        await no_app_db_session.commit()

        assert await repo.get(user.id) is None

    async def test_delete_by_id(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert user.id is not None

        deleted = await repo.delete_by_id(user.id)

        assert deleted is True

        await no_app_db_session.commit()

        assert await repo.get(user.id) is None

    async def test_delete_by_id_returns_false_when_missing(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        assert await repo.delete_by_id(999999) is False

    async def test_save(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )

        await repo.save(user)

        assert user in no_app_db_session

        await no_app_db_session.commit()

        assert user.id is not None

    async def test_exists(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        assert await repo.exists() is False
        assert await repo.exists(UserAccount.username == "missing") is False

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert await repo.exists() is True
        assert await repo.exists(UserAccount.username == "test") is True
        assert await repo.exists(UserAccount.username == "missing") is False

    async def test_get_base_query(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        stmt = repo.get_base_query(
            UserAccount.username == "test",
        )

        result = await no_app_db_session.scalars(stmt)

        assert result.all() == []

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        result = await no_app_db_session.scalars(stmt)

        assert result.all() == [user]

    async def test_delete_where(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        users = [
            UserAccount(
                username=f"user{i}",
                password="test",
                email=f"user{i}@example.com",
            )
            for i in range(3)
        ]

        for user in users:
            await repo.save(user)

        await no_app_db_session.commit()

        deleted = await repo.delete_where(
            UserAccount.username == "user1",
        )

        assert deleted == 1

        await no_app_db_session.commit()

        assert await repo.get(users[0].id) is not None
        assert await repo.get(users[1].id) is None
        assert await repo.get(users[2].id) is not None
