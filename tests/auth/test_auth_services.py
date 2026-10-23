import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.db.registry import RefreshToken, UserAccount
from fastapi_orderly.modules.auth.deps import (
    get_authentication_service,
    get_refresh_token_repository,
    get_user_repository,
)
from fastapi_orderly.modules.auth.dtos import (
    RegisterUserRequest,
    UserContactInfo,
)
from fastapi_orderly.modules.auth.errors import (
    InvalidRefreshTokenError,
    UserAlreadyRegisteredError,
    WrongCredentialsError,
)
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

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
        tokenizer: AuthTokenizer,
    ) -> None:
        login = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )

        old_claims = tokenizer.decode(login.refresh)
        old_hash = authentication_service.hasher.hash_token(login.refresh).encode("utf-8")

        old_record = await authentication_service.refresh_token_repository.get_by_hash(old_hash)
        assert old_record is not None
        assert old_record.is_used is False

        result = await authentication_service.refresh_token(login.refresh)

        assert result.access
        assert result.refresh
        assert result.refresh != login.refresh

        access_claims = tokenizer.decode(result.access)
        refresh_claims = tokenizer.decode(result.refresh)

        assert access_claims.sub == str(active_user.id)
        assert access_claims.iss == "orderly:login"
        assert access_claims.aud == "orderly"
        assert access_claims.typ == TokenType.ACCESS

        assert refresh_claims.sub == str(active_user.id)
        assert refresh_claims.iss == "orderly:login"
        assert refresh_claims.aud == "orderly:login"
        assert refresh_claims.typ == TokenType.REFRESH
        assert refresh_claims.family_id == old_claims.family_id

        assert access_claims.jti != refresh_claims.jti
        assert refresh_claims.jti != old_claims.jti

        # The old token is consumed.
        await authentication_service.refresh_token_repository.session.refresh(old_record)
        assert old_record.is_used is True

        # The replacement is persisted and unused.
        new_hash = authentication_service.hasher.hash_token(result.refresh).encode("utf-8")
        new_record = await authentication_service.refresh_token_repository.get_by_hash(new_hash)

        assert new_record is not None
        assert new_record.user_id == active_user.id
        assert new_record.family_id == old_claims.family_id
        assert new_record.is_used is False

        assert access_claims.exp - access_claims.iat == timedelta(minutes=15)
        assert refresh_claims.exp - refresh_claims.iat == timedelta(hours=48)

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_deletes_entire_family(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
        tokenizer: AuthTokenizer,
    ) -> None:
        login = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )

        first_claims = tokenizer.decode(login.refresh)

        # First rotation: R1 -> R2.
        rotated = await authentication_service.refresh_token(login.refresh)

        second_hash = authentication_service.hasher.hash_token(rotated.refresh).encode("utf-8")

        second_record = await authentication_service.refresh_token_repository.get_by_hash(
            second_hash
        )
        assert second_record is not None
        assert second_record.family_id == first_claims.family_id

        # Replay R1. It must revoke R2 and every other token in this family.
        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(login.refresh)

        assert (
            await authentication_service.refresh_token_repository.get_by_hash(second_hash)
        ) is None

        assert (
            await authentication_service.refresh_token_repository.get_by_hash(
                authentication_service.hasher.hash_token(login.refresh).encode("utf-8")
            )
        ) is None

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_does_not_delete_other_families(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
    ) -> None:
        first_login = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )
        second_login = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )

        # Rotate the first family.
        rotated_first = await authentication_service.refresh_token(first_login.refresh)

        second_family_hash = authentication_service.hasher.hash_token(second_login.refresh).encode(
            "utf-8"
        )

        second_family_record = await authentication_service.refresh_token_repository.get_by_hash(
            second_family_hash
        )
        assert second_family_record is not None

        # Reusing the first family's consumed token revokes only that family.
        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(first_login.refresh)

        assert (
            await authentication_service.refresh_token_repository.get_by_hash(
                authentication_service.hasher.hash_token(rotated_first.refresh).encode("utf-8")
            )
        ) is None

        assert (
            await authentication_service.refresh_token_repository.get_by_hash(second_family_hash)
        ) is not None

        # The unrelated family's refresh token remains usable.
        second_rotated = await authentication_service.refresh_token(second_login.refresh)
        assert second_rotated.access
        assert second_rotated.refresh

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(
        self,
        authentication_service: AuthenticationService,
    ) -> None:
        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token("not-a-valid-token")

        assert await authentication_service.refresh_token_repository.count() == 0

    @pytest.mark.asyncio
    async def test_refresh_token_access_token_is_rejected(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
    ) -> None:
        login = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(login.access)

        # Rejecting an access token must not consume or delete the refresh token.
        refresh_hash = authentication_service.hasher.hash_token(login.refresh).encode("utf-8")
        record = await authentication_service.refresh_token_repository.get_by_hash(refresh_hash)

        assert record is not None
        assert record.is_used is False

    @pytest.mark.asyncio
    async def test_refresh_token_inactive_user_is_rejected(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
    ) -> None:
        login = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )

        active_user.is_active = False
        await authentication_service.refresh_token_repository.session.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(login.refresh)

        # The token must not be rotated for an inactive user.
        assert await authentication_service.refresh_token_repository.count() == 1

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_claims_and_records(
        self,
        authentication_service: AuthenticationService,
        active_user: UserAccount,
        tokenizer: AuthTokenizer,
    ) -> None:
        from datetime import UTC, datetime, timedelta
        from uuid import uuid4

        login = await authentication_service.token_login(
            email=active_user.email,
            password=active_user.password,
        )
        valid_claims = tokenizer.decode(login.refresh)

        # Each modified token must fail validation.
        invalid_claims = [
            valid_claims.model_copy(update={"typ": TokenType.ACCESS}),
            valid_claims.model_copy(update={"iss": "wrong-issuer"}),
            valid_claims.model_copy(update={"aud": "wrong-audience"}),
            valid_claims.model_copy(update={"exp": datetime.now(UTC) - timedelta(minutes=1)}),
            valid_claims.model_copy(update={"iat": datetime.now(UTC) + timedelta(minutes=1)}),
            valid_claims.model_copy(update={"family_id": None}),
            valid_claims.model_copy(update={"sub": "not-an-integer"}),
        ]

        for claims in invalid_claims:
            # Bypass PASETO signing so the service receives a correctly signed
            # token containing the modified claims.
            token = authentication_service.tokenizer.encode(claims).decode("ascii")

            with pytest.raises(InvalidRefreshTokenError):
                await authentication_service.refresh_token(token)

        # A validly signed token whose hash is not in the database.
        unknown_token = authentication_service.tokenizer.encode(
            valid_claims.model_copy(update={"jti": "unknown-jti"})
        ).decode("ascii")

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(unknown_token)

        # Token subject doesn't match the user ID stored in the database.
        mismatched_sub = valid_claims.model_copy(update={"sub": str(active_user.id + 1)})
        mismatched_sub_token = authentication_service.tokenizer.encode(mismatched_sub).decode(
            "ascii"
        )

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(mismatched_sub_token)

        # Token family doesn't match the database record.
        mismatched_family = valid_claims.model_copy(update={"family_id": uuid4()})
        mismatched_family_token = authentication_service.tokenizer.encode(mismatched_family).decode(
            "ascii"
        )

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(mismatched_family_token)

        # Inactive / unverified users cannot refresh.
        active_user.is_active = False
        await authentication_service.refresh_token_repository.session.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(login.refresh)

        active_user.is_active = True
        active_user.is_email_verified = False
        await authentication_service.refresh_token_repository.session.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(login.refresh)

        # Cover record.user_id != user_id
        claims = tokenizer.decode(login.refresh).model_copy(update={"sub": str(active_user.id + 1)})
        token = tokenizer.encode(claims).decode("ascii")

        record = RefreshToken(
            user_id=active_user.id,
            token_hash=authentication_service.hasher.hash_token(token).encode("utf-8"),
            family_id=claims.family_id,
        )
        await authentication_service.refresh_token_repository.save(record)
        await authentication_service.refresh_token_repository.session.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(token)

        # Cover record.family_id != claims.family_id
        claims = tokenizer.decode(login.refresh).model_copy(update={"family_id": uuid.uuid4()})
        token = tokenizer.encode(claims).decode("ascii")

        record = RefreshToken(
            user_id=active_user.id,
            token_hash=authentication_service.hasher.hash_token(token).encode("utf-8"),
            family_id=uuid.uuid4(),  # Deliberately differs from the claim.
        )
        await authentication_service.refresh_token_repository.save(record)
        await authentication_service.refresh_token_repository.session.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await authentication_service.refresh_token(token)
