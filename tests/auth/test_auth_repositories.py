from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.modules.auth.models import (
    RefreshToken,
    UserAccount,
    UserPermissions,
)
from fastapi_orderly.modules.auth.repositories import (
    RefreshTokenRepository,
    UserPermissionsRepository,
    UserRepository,
)


class TestUserRepository:
    async def test_get_by_username(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = UserRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert await repo.get_by_username("test") == user
        assert await repo.get_by_username("missing") is None

    async def test_get_by_email(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = UserRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert await repo.get_by_email("test@example.com") == user
        assert await repo.get_by_email("missing@example.com") is None

    async def test_get_by_username_or_email(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = UserRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert await repo.get_by_username_or_email("test") == user
        assert await repo.get_by_username_or_email("test@example.com") == user
        assert await repo.get_by_username_or_email("missing") is None

    async def test_username_exists(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = UserRepository(no_app_db_session)

        assert await repo.username_exists("test") is False

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert await repo.username_exists("test") is True
        assert await repo.username_exists("missing") is False

    async def test_email_exists(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = UserRepository(no_app_db_session)

        assert await repo.email_exists("test@example.com") is False

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert await repo.email_exists("test@example.com") is True
        assert await repo.email_exists("missing@example.com") is False


class TestUserPermissionsRepository:
    async def test_get_by_user_and_permission(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        user_repo = UserRepository(no_app_db_session)
        repo = UserPermissionsRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await user_repo.save(user)
        await no_app_db_session.commit()

        permission = UserPermissions(
            user_id=user.id,
            perm_code="users.read",
        )
        await repo.save(permission)
        await no_app_db_session.commit()

        assert (
            await repo.get_by_user_and_permission(
                user.id,
                "users.read",
            )
            == permission
        )

        assert (
            await repo.get_by_user_and_permission(
                user.id,
                "users.write",
            )
            is None
        )

        assert (
            await repo.get_by_user_and_permission(
                999999,
                "users.read",
            )
            is None
        )

    async def test_get_user_permissions(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        user_repo = UserRepository(no_app_db_session)
        repo = UserPermissionsRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await user_repo.save(user)
        await no_app_db_session.commit()

        permissions = [
            UserPermissions(user_id=user.id, perm_code="users.write"),
            UserPermissions(user_id=user.id, perm_code="users.read"),
            UserPermissions(user_id=user.id, perm_code="admin.read"),
        ]

        for permission in permissions:
            await repo.save(permission)

        await no_app_db_session.commit()

        result = await repo.get_user_permissions(user.id)

        assert result == [
            permissions[2],
            permissions[1],
            permissions[0],
        ]

        assert await repo.get_user_permissions(999999) == []

    async def test_has_permission(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        user_repo = UserRepository(no_app_db_session)
        repo = UserPermissionsRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
            is_admin=False,
        )
        await user_repo.save(user)
        await no_app_db_session.commit()

        permission = UserPermissions(
            user_id=user.id,
            perm_code="users.read",
        )
        await repo.save(permission)
        await no_app_db_session.commit()

        await no_app_db_session.refresh(user)

        assert await repo.has_permission(user, "users.read") is True
        assert await repo.has_permission(user, "users.write") is False

    async def test_has_permission_returns_true_for_admin(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = UserPermissionsRepository(no_app_db_session)

        user = UserAccount(
            username="admin",
            password="password",
            email="admin@example.com",
            is_admin=True,
        )
        no_app_db_session.add(user)
        await no_app_db_session.commit()

        assert await repo.has_permission(user, "anything") is True

    async def test_has_non_admin_permission(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        user_repo = UserRepository(no_app_db_session)
        repo = UserPermissionsRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await user_repo.save(user)
        await no_app_db_session.commit()

        permission = UserPermissions(
            user_id=user.id,
            perm_code="users.read",
        )
        await repo.save(permission)
        await no_app_db_session.commit()

        assert (
            await repo.has_non_admin_permission(
                user.id,
                "users.read",
            )
            is True
        )

        assert (
            await repo.has_non_admin_permission(
                user.id,
                "users.write",
            )
            is False
        )

        assert (
            await repo.has_non_admin_permission(
                999999,
                "users.read",
            )
            is False
        )

    async def test_delete_permission(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        user_repo = UserRepository(no_app_db_session)
        repo = UserPermissionsRepository(no_app_db_session)

        user = UserAccount(
            username="test",
            password="password",
            email="test@example.com",
        )
        await user_repo.save(user)
        await no_app_db_session.commit()

        permission = UserPermissions(
            user_id=user.id,
            perm_code="users.read",
        )
        await repo.save(permission)
        await no_app_db_session.commit()

        assert (
            await repo.delete_permission(
                user.id,
                "users.read",
            )
            is True
        )

        await no_app_db_session.commit()

        assert (
            await repo.get_by_user_and_permission(
                user.id,
                "users.read",
            )
            is None
        )

        assert (
            await repo.delete_permission(
                user.id,
                "users.read",
            )
            is False
        )


class TestRefreshTokenRepository:
    async def test_get_by_hash(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        token_hash = b"token-hash"

        token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
        )
        await repo.save(token)
        await no_app_db_session.commit()

        assert await repo.get_by_hash(token_hash) == token
        assert await repo.get_by_hash(b"missing") is None

    async def test_exists_by_hash(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        token_hash = b"token-hash"

        assert await repo.exists_by_hash(token_hash) is False

        token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
        )
        await repo.save(token)
        await no_app_db_session.commit()

        assert await repo.exists_by_hash(token_hash) is True
        assert await repo.exists_by_hash(b"missing") is False

    async def test_delete_by_hash(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        token_hash = b"token-hash"

        token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
        )
        await repo.save(token)
        await no_app_db_session.commit()

        assert await repo.delete_by_hash(token_hash) is True

        await no_app_db_session.commit()

        assert await repo.get_by_hash(token_hash) is None

        assert await repo.delete_by_hash(token_hash) is False

    async def test_get_user_tokens(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        users = []
        for i in range(1, 3):
            user = UserAccount(
                username=f"test-{i}",
                email=f"test-{i}@example.com",
                password="test",
            )
            no_app_db_session.add(user)
            users.append(user)
        await no_app_db_session.flush()

        tokens = [
            RefreshToken(user_id=users[0].id, token_hash=b"token-1"),
            RefreshToken(user_id=users[0].id, token_hash=b"token-2"),
            RefreshToken(user_id=users[1].id, token_hash=b"token-3"),
        ]

        for token in tokens:
            await repo.save(token)

        await no_app_db_session.commit()

        assert await repo.get_user_tokens(users[0].id) == tokens[:2]
        assert await repo.get_user_tokens(users[1].id) == [tokens[2]]
        assert await repo.get_user_tokens(999999) == []

    async def test_delete_user_tokens(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        users = []
        for i in range(1, 3):
            user = UserAccount(
                username=f"test-{i}",
                email=f"test-{i}@example.com",
                password="test",
            )
            no_app_db_session.add(user)
            users.append(user)
        await no_app_db_session.flush()
        user_tokens = [
            RefreshToken(user_id=users[0].id, token_hash=b"token-1"),
            RefreshToken(user_id=users[0].id, token_hash=b"token-2"),
        ]
        other_token = RefreshToken(
            user_id=users[1].id,
            token_hash=b"token-3",
        )

        for token in [*user_tokens, other_token]:
            await repo.save(token)

        await no_app_db_session.commit()

        assert await repo.delete_user_tokens(users[0].id) == 2

        await no_app_db_session.commit()

        assert await repo.get_user_tokens(users[0].id) == []
        assert await repo.get_user_tokens(users[1].id) == [other_token]

    async def test_delete_user_tokens_returns_zero_when_missing(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        assert await repo.delete_user_tokens(999999) == 0
