import uuid

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

    async def test_get_by_username_or_email_and_active(
        self,
        no_app_db_session: AsyncSession,
    ) -> None:
        repo = UserRepository(no_app_db_session)

        user = UserAccount(
            username="test", password="password", email="test@example.com", is_active=False
        )
        await repo.save(user)
        await no_app_db_session.commit()

        assert await repo.get_by_username_or_email_and_active("test") is None
        assert await repo.get_by_username_or_email_and_active("test@example.com") is None
        user.is_active = True
        await no_app_db_session.commit()
        assert await repo.get_by_username_or_email_and_active("test") == user
        assert await repo.get_by_username_or_email_and_active("test@example.com") == user

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
            family_id=uuid.uuid4(),
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
            family_id=uuid.uuid4(),
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
            family_id=uuid.uuid4(),
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
            RefreshToken(
                user_id=users[0].id,
                token_hash=b"token-1",
                family_id=uuid.uuid4(),
            ),
            RefreshToken(
                user_id=users[0].id,
                token_hash=b"token-2",
                family_id=uuid.uuid4(),
            ),
            RefreshToken(
                user_id=users[1].id,
                token_hash=b"token-3",
                family_id=uuid.uuid4(),
            ),
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
            RefreshToken(
                user_id=users[0].id,
                token_hash=b"token-1",
                family_id=uuid.uuid4(),
            ),
            RefreshToken(
                user_id=users[0].id,
                token_hash=b"token-2",
                family_id=uuid.uuid4(),
            ),
        ]
        other_token = RefreshToken(
            user_id=users[1].id,
            token_hash=b"token-3",
            family_id=uuid.uuid4(),
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

    async def test_get_by_hash_for_update(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)
        token_hash = b"token-hash"

        token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            family_id=uuid.uuid4(),
        )
        await repo.save(token)
        await no_app_db_session.commit()

        result = await repo.get_by_hash_for_update(token_hash)

        assert result == token
        assert result is not None
        assert result.token_hash == token_hash

        assert await repo.get_by_hash_for_update(b"missing") is None

    async def test_mark_used(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        token = RefreshToken(
            user_id=user.id,
            token_hash=b"token-hash",
            family_id=uuid.uuid4(),
        )
        await repo.save(token)
        await no_app_db_session.commit()

        assert token.is_used is False

        await repo.mark_used(token)
        await no_app_db_session.commit()

        # Reload to verify the persisted database state.
        await no_app_db_session.refresh(token)

        assert token.is_used is True

    async def test_mark_used_does_not_affect_other_tokens(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        token = RefreshToken(
            user_id=user.id,
            token_hash=b"token-1",
            family_id=uuid.uuid4(),
        )
        other_token = RefreshToken(
            user_id=user.id,
            token_hash=b"token-2",
            family_id=uuid.uuid4(),
        )

        await repo.save(token)
        await repo.save(other_token)
        await no_app_db_session.commit()

        await repo.mark_used(token)
        await no_app_db_session.commit()

        await no_app_db_session.refresh(token)
        await no_app_db_session.refresh(other_token)

        assert token.is_used is True
        assert other_token.is_used is False

    async def test_delete_family(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        family_id = uuid.uuid4()
        other_family_id = uuid.uuid4()

        family_tokens = [
            RefreshToken(
                user_id=user.id,
                token_hash=b"token-1",
                family_id=family_id,
            ),
            RefreshToken(
                user_id=user.id,
                token_hash=b"token-2",
                family_id=family_id,
                is_used=True,
            ),
        ]
        other_token = RefreshToken(
            user_id=user.id,
            token_hash=b"token-3",
            family_id=other_family_id,
        )

        for token in [*family_tokens, other_token]:
            await repo.save(token)

        await no_app_db_session.commit()

        await repo.delete_family(family_id)
        await no_app_db_session.commit()

        assert await repo.get_by_hash(b"token-1") is None
        assert await repo.get_by_hash(b"token-2") is None
        assert await repo.get_by_hash(b"token-3") == other_token

    async def test_delete_family_when_missing(
        self,
        no_app_db_session: AsyncSession,
        user: UserAccount,
    ) -> None:
        repo = RefreshTokenRepository(no_app_db_session)

        token = RefreshToken(
            user_id=user.id,
            token_hash=b"token-1",
            family_id=uuid.uuid4(),
        )
        await repo.save(token)
        await no_app_db_session.commit()

        await repo.delete_family(uuid.uuid4())
        await no_app_db_session.commit()

        assert await repo.get_by_hash(b"token-1") == token
