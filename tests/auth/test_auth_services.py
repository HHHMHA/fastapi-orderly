import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.dtos import RegisterUserRequest
from fastapi_orderly.modules.auth.errors import UserAlreadyRegisteredError
from fastapi_orderly.modules.auth.services import UserService
from tests.utils import FakeHasher


class TestUserService:
    @pytest.mark.asyncio
    async def test_register_user(
        self,
        no_app_db_session: AsyncSession,
        user_service: UserService,
    ) -> None:
        request = RegisterUserRequest(
            username="newuser",
            email="  NewUser@Example.COM  ",
            password=SecretStr("secure-password"),
        )

        service_user = await user_service.register_user(request)

        user = await user_service.user_repository.get_by_email("newuser@example.com")
        assert service_user == user
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.password == FakeHasher().hash("secure-password")
        assert user.password == "secure-password"
        assert user.is_active is True
        assert user.is_email_verified is False
        assert user.is_admin is False

    @pytest.mark.asyncio
    async def test_register_user_with_duplicate_email(
        self,
        user: UserAccount,
        user_service: UserService,
        no_app_db_session: AsyncSession,
    ) -> None:
        request = RegisterUserRequest(
            username="anotheruser",
            email=user.email,
            password=SecretStr("secure-password"),
        )

        with pytest.raises(UserAlreadyRegisteredError):
            await user_service.register_user(request)

        assert await user_service.user_repository.get_by_username("anotheruser") is None

    @pytest.mark.asyncio
    async def test_register_user_with_duplicate_username(
        self,
        user: UserAccount,
        user_service: UserService,
        no_app_db_session: AsyncSession,
    ) -> None:
        request = RegisterUserRequest(
            username=user.username,
            email="another@example.com",
            password=SecretStr("secure-password"),
        )

        with pytest.raises(UserAlreadyRegisteredError):
            await user_service.register_user(request)

        assert await user_service.user_repository.get_by_email("another@example.com") is None

    @pytest.mark.asyncio
    async def test_register_user_with_duplicate_email_and_username(
        self,
        user: UserAccount,
        user_service: UserService,
        no_app_db_session: AsyncSession,
    ) -> None:
        request = RegisterUserRequest(
            username=user.username,
            email=user.email,
            password=SecretStr("secure-password"),
        )

        with pytest.raises(UserAlreadyRegisteredError):
            await user_service.register_user(request)

        assert await user_service.user_repository.count() == 1

    def test_register_user_with_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            RegisterUserRequest(
                username="newuser",
                email="not-an-email",
                password=SecretStr("secure-password"),
            )

    def test_user_already_exist_empty_error(self) -> None:
        with pytest.raises(ValueError):
            UserAlreadyRegisteredError()
