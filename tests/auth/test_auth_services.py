from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.deps import (
    get_authentication_service,
    get_refresh_token_repository,
    get_user_repository,
)
from fastapi_orderly.modules.auth.dtos import (
    RegisterUserRequest,
    UserContactInfo,
)
from fastapi_orderly.modules.auth.errors import UserAlreadyRegisteredError, WrongCredentialsError
from fastapi_orderly.modules.auth.hasher import get_hasher
from fastapi_orderly.modules.auth.services import AuthenticationService, UserService
from fastapi_orderly.modules.auth.token import AuthTokenizer, TokenType
from fastapi_orderly.modules.otp.errors import OTPCodeInvalidError
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

    @pytest.mark.asyncio
    async def test_resend_otp(
        self,
        user: UserAccount,
        user_service: UserService,
    ) -> None:
        with patch.object(
            user_service.otp_service,
            "generate_and_send",
            new_callable=AsyncMock,
        ) as mock_generate_and_send:
            await user_service.resend_otp(user.email)

        mock_generate_and_send.assert_awaited_once_with(
            user.id,
            UserContactInfo.model_validate(user),
        )

    @pytest.mark.asyncio
    async def test_resend_otp_for_nonexistent_user(
        self,
        user_service: UserService,
    ) -> None:
        with patch.object(
            user_service.otp_service,
            "generate_and_send",
            new_callable=AsyncMock,
        ) as mock_generate_and_send:
            result = await user_service.resend_otp("nonexistent@example.com")

        assert result is None
        mock_generate_and_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_user_email_success(
        self,
        user: UserAccount,
        user_service: UserService,
        no_app_db_session: AsyncSession,
    ) -> None:
        user.is_email_verified = False
        code = "123456"

        with patch.object(
            user_service.otp_service,
            "check_otp",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_check_otp:
            result = await user_service.verify_user_email(
                email=user.email,
                code=code,
            )

        assert result is True
        assert user.is_email_verified is True

        mock_check_otp.assert_awaited_once_with(user.id, code)

    @pytest.mark.asyncio
    async def test_verify_user_email_commits_changes(
        self,
        user: UserAccount,
        user_service: UserService,
        no_app_db_session: AsyncSession,
    ) -> None:
        user.is_email_verified = False

        with (
            patch.object(
                user_service.otp_service,
                "check_otp",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch.object(
                user_service.user_repository.session,
                "commit",
                new_callable=AsyncMock,
            ) as mock_commit,
        ):
            result = await user_service.verify_user_email(
                email=user.email,
                code="123456",
            )

        assert result is True
        assert user.is_email_verified is True
        mock_commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_user_email_nonexistent_user(
        self,
        user_service: UserService,
    ) -> None:
        with (
            patch.object(
                user_service.user_repository,
                "get_by_email",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                user_service.otp_service,
                "check_otp",
                new_callable=AsyncMock,
            ) as mock_check_otp,
        ):
            result = await user_service.verify_user_email(
                email="nonexistent@example.com",
                code="123456",
            )

        assert result is False
        mock_check_otp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_user_email_already_verified(
        self,
        user: UserAccount,
        user_service: UserService,
    ) -> None:
        user.is_email_verified = True

        with patch.object(
            user_service.otp_service,
            "check_otp",
            new_callable=AsyncMock,
        ) as mock_check_otp:
            result = await user_service.verify_user_email(
                email=user.email,
                code="123456",
            )

        assert result is False
        mock_check_otp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_user_email_invalid_otp(
        self,
        user: UserAccount,
        user_service: UserService,
    ) -> None:
        user.is_email_verified = False

        with (
            patch.object(
                user_service.otp_service,
                "check_otp",
                new_callable=AsyncMock,
                return_value=False,
            ) as mock_check_otp,
            pytest.raises(OTPCodeInvalidError),
        ):
            await user_service.verify_user_email(
                email=user.email,
                code="000000",
            )

        assert user.is_email_verified is False
        mock_check_otp.assert_awaited_once_with(user.id, "000000")

    @pytest.mark.asyncio
    async def test_verify_user_email_invalid_otp_does_not_commit(
        self,
        user: UserAccount,
        user_service: UserService,
        no_app_db_session: AsyncSession,
    ) -> None:
        user.is_email_verified = False

        with (
            patch.object(
                user_service.otp_service,
                "check_otp",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch.object(
                user_service.user_repository.session,
                "commit",
                new_callable=AsyncMock,
            ) as mock_commit,
            pytest.raises(OTPCodeInvalidError),
        ):
            await user_service.verify_user_email(
                email=user.email,
                code="000000",
            )

        assert user.is_email_verified is False
        mock_commit.assert_not_awaited()


class TestAuthenticationService:
    @pytest.mark.asyncio
    async def test_token_login_success(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
        tokenizer: AuthTokenizer,
    ) -> None:
        result = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )

        assert result.access is not None
        assert result.refresh is not None

        access_claims = tokenizer.decode(result.access)
        refresh_claims = tokenizer.decode(result.refresh)

        assert access_claims.sub == str(active_user.id)
        assert access_claims.iss == "orderly:login"
        assert access_claims.aud == "orderly"
        assert access_claims.typ == TokenType.ACCESS
        assert access_claims.jti
        assert access_claims.iat is not None
        assert access_claims.exp is not None

        assert refresh_claims.sub == str(active_user.id)
        assert refresh_claims.iss == "orderly:login"
        assert refresh_claims.aud == "orderly:login"
        assert refresh_claims.typ == TokenType.REFRESH
        assert refresh_claims.jti
        assert refresh_claims.iat is not None
        assert refresh_claims.exp is not None

        assert access_claims.jti != refresh_claims.jti

        assert access_claims.exp - access_claims.iat == timedelta(minutes=15)
        assert refresh_claims.exp - refresh_claims.iat == timedelta(hours=48)

        saved_token = await authentication_service.refresh_token_repository.get_by_hash(
            authentication_service.hasher.hash_token(result.refresh).encode("utf-8")
        )

        assert saved_token is not None
        assert saved_token.user_id == active_user.id

    @pytest.mark.asyncio
    async def test_token_login_user_does_not_exist(
        self,
        authentication_service: AuthenticationService,
        tokenizer: AuthTokenizer,
    ) -> None:
        with (
            pytest.raises(WrongCredentialsError),
            patch.object(
                authentication_service.hasher, "verify", new_callable=MagicMock
            ) as mock_verify,
        ):
            result = await authentication_service.token_login(
                email="missing@example.com",
                password="some-password",
            )
            assert result is None

        mock_verify.assert_called_once_with(
            "some-password",
            authentication_service.hasher.dummy_hash,
        )
        assert await authentication_service.refresh_token_repository.count() == 0

    @pytest.mark.asyncio
    async def test_token_login_wrong_password(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
        tokenizer: AuthTokenizer,
    ) -> None:
        with (
            pytest.raises(WrongCredentialsError),
        ):
            result = await authentication_service.token_login(
                email=active_user.email,
                password="some-password",
            )
            assert result is None

        assert await authentication_service.refresh_token_repository.count() == 0

    @pytest.mark.asyncio
    async def test_token_login_inactive_user(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
        tokenizer: AuthTokenizer,
    ) -> None:
        with (
            pytest.raises(WrongCredentialsError),
        ):
            active_user.is_email_verified = False
            result = await authentication_service.token_login(
                email=active_user.email,
                password=active_user.password,
            )
            assert result is None

        active_user.is_email_verified = True
        active_user.is_active = False
        with (
            pytest.raises(WrongCredentialsError),
        ):
            result = await authentication_service.token_login(
                email=active_user.email,
                password=active_user.password,
            )
            assert result is None

        assert await authentication_service.refresh_token_repository.count() == 0

    @pytest.mark.asyncio
    async def test_token_login_success_integration(
        self,
        no_app_db_session: AsyncSession,
        tokenizer: AuthTokenizer,
    ) -> None:
        hasher = get_hasher()

        user = UserAccount(
            email="test@example.com",
            username="test",
            password=hasher.hash("password"),
            is_email_verified=True,
            is_active=True,
        )
        no_app_db_session.add(user)
        await no_app_db_session.flush()
        authentication_service = get_authentication_service(
            user_repository=get_user_repository(session=no_app_db_session),
            refresh_token_repository=get_refresh_token_repository(session=no_app_db_session),
            hasher=hasher,
            tokenizer=tokenizer,
        )

        result = await authentication_service.token_login(
            email=user.email,
            password="password",
        )

        assert user.password != "password"
        assert result.access is not None
        assert result.refresh is not None

        access_claims = tokenizer.decode(result.access)
        refresh_claims = tokenizer.decode(result.refresh)

        assert access_claims.sub == str(user.id)
        assert access_claims.iss == "orderly:login"
        assert access_claims.aud == "orderly"
        assert access_claims.typ == TokenType.ACCESS
        assert access_claims.jti
        assert access_claims.iat is not None
        assert access_claims.exp is not None

        assert refresh_claims.sub == str(user.id)
        assert refresh_claims.iss == "orderly:login"
        assert refresh_claims.aud == "orderly:login"
        assert refresh_claims.typ == TokenType.REFRESH
        assert refresh_claims.jti
        assert refresh_claims.iat is not None
        assert refresh_claims.exp is not None

        assert access_claims.jti != refresh_claims.jti

        assert access_claims.exp - access_claims.iat == timedelta(minutes=15)
        assert refresh_claims.exp - refresh_claims.iat == timedelta(hours=48)

        saved_token = await authentication_service.refresh_token_repository.get_by_hash(
            authentication_service.hasher.hash_token(result.refresh).encode("utf-8")
        )

        assert saved_token is not None
        assert saved_token.user_id == user.id
