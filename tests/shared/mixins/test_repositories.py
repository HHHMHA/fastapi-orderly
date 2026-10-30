import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.modules.auth.models import UserAccount
from fastapi_orderly.shared.mixins.reposotories import ActivatorRepositoryMixin, RepositoryBase


class FakeUserRepository(ActivatorRepositoryMixin[UserAccount]):
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

    async def test_run(
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

        result = await repo.run(repo.get_base_query())

        assert result == users

    async def test_get_or_else_returns_existing(
        self, no_app_db_session: AsyncSession, user: UserAccount
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        handler_called = False

        def handler() -> UserAccount:
            nonlocal handler_called
            handler_called = True
            return UserAccount(
                username="fallback",
                password="test",
                email="fallback@example.com",
            )

        result = await repo.get_or_else(
            UserAccount.username == "test",
            handler=handler,
        )

        assert result is user
        assert handler_called is False

    async def test_get_or_else_calls_handler_when_missing(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)
        fallback = UserAccount(
            username="fallback",
            password="test",
            email="fallback@example.com",
        )

        result = await repo.get_or_else(
            UserAccount.username == "missing",
            handler=lambda: fallback,
        )

        assert result is fallback

    async def test_get_or_else_returns_none_when_handler_returns_none(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        result = await repo.get_or_else(
            UserAccount.username == "missing",
            handler=lambda: None,
        )

        assert result is None

    async def test_get_or_merge_inserts_when_missing(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)
        incoming = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
        )

        result = await repo.get_or_merge(
            UserAccount.username == "test",
            handler=lambda: incoming,
        )

        assert result is incoming
        assert incoming in no_app_db_session

        await no_app_db_session.commit()

        assert incoming.id is not None
        assert await repo.get(incoming.id) is incoming

    async def test_get_or_merge_returns_existing_when_handler_returns_none(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)
        existing = UserAccount(
            username="existing",
            password="original",
            email="existing@example.com",
        )
        await repo.save(existing)
        await no_app_db_session.commit()

        result = await repo.get_or_merge(
            UserAccount.username == "existing",
            handler=lambda: None,
        )

        assert result is existing
        assert existing.password == "original"
        assert existing.email == "existing@example.com"

    async def test_get_or_merge_updates_existing(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)
        existing = UserAccount(
            username="test",
            password="original",
            email="original@example.com",
        )
        await repo.save(existing)
        await no_app_db_session.commit()

        incoming = UserAccount(
            username="test",
            password="updated",
            email="updated@example.com",
        )

        result = await repo.get_or_merge(
            UserAccount.username == "test",
            handler=lambda: incoming,
        )

        assert result is existing
        assert existing.password == "updated"
        assert existing.email == "updated@example.com"

        await no_app_db_session.commit()

        refreshed = await repo.get(existing.id)
        assert refreshed is not None
        assert refreshed is existing
        assert refreshed.password == "updated"
        assert refreshed.email == "updated@example.com"

    async def test_get_or_merge_excludes_fields(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)
        existing = UserAccount(
            username="test",
            password="original",
            email="original@example.com",
        )
        await repo.save(existing)
        await no_app_db_session.commit()

        incoming = UserAccount(
            username="test",
            password="updated",
            email="updated@example.com",
        )

        result = await repo.get_or_merge(
            UserAccount.username == "test",
            handler=lambda: incoming,
            exclude=(UserAccount.password,),
        )

        assert result is existing
        assert existing.password == "original"
        assert existing.email == "updated@example.com"

    async def test_get_existing_fields(
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

        result = await repo.get_existing_fields(
            username=UserAccount.username == "test",
            email=UserAccount.email == "test@example.com",
            missing=UserAccount.username == "missing",
        )

        assert result == {"username", "email"}

    async def test_get_existing_fields_returns_empty_set_when_no_match(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        result = await repo.get_existing_fields(
            username=UserAccount.username == "missing",
            email=UserAccount.email == "missing@example.com",
        )

        assert result == set()

    async def test_get_existing_fields_returns_empty_set_without_conditions(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        result = await repo.get_existing_fields()

        assert result == set()

    async def test_filter_is_active(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="test",
            email="test@example.com",
            is_active=False,
        )
        await repo.save(user)
        await no_app_db_session.commit()

        result = await repo.run(repo.filter_is_active())

        assert not result

        result = await repo.run(repo.filter_is_disabled())

        assert result == [user]

        user.is_active = True
        await repo.session.commit()

        result = await repo.run(repo.filter_is_active())

        assert result == [user]

        result = await repo.run(repo.filter_is_disabled())

        assert not result

    async def test_bulk_insert_empty(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = FakeUserRepository(no_app_db_session)

        await repo.bulk_insert([])

        assert await repo.count() == 0

    async def test_bulk_insert(
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

        await repo.bulk_insert(users)

        result = await repo.all()

        assert len(result) == 3
        assert {user.username for user in result} == {
            "user0",
            "user1",
            "user2",
        }
        assert {user.email for user in result} == {
            "user0@example.com",
            "user1@example.com",
            "user2@example.com",
        }
        assert all(user.password == "test" for user in result)
