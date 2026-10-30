import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from fastapi_orderly.core.db.registry import RefreshToken, UserAccount
from fastapi_orderly.core.loggers import logger
from fastapi_orderly.modules.auth.dtos import (
    LoginTokenResponse,
    RegisterUserRequest,
    UserContactInfo,
)
from fastapi_orderly.modules.auth.errors import (
    AccountLockedError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    UserAlreadyRegisteredError,
    WrongCredentialsError,
)
from fastapi_orderly.modules.auth.hasher import Hasher
from fastapi_orderly.modules.auth.repositories import (
    RefreshTokenRepository,
    UserPermissionsRepository,
    UserRepository,
)
from fastapi_orderly.modules.auth.token import AuthTokenizer, TokenClaims, TokenType
from fastapi_orderly.modules.otp.errors import OTPCodeInvalidError
from fastapi_orderly.modules.otp.services import OTPService


@dataclass
class AuthenticationService:
    user_repository: UserRepository
    refresh_token_repository: RefreshTokenRepository
    hasher: Hasher
    tokenizer: AuthTokenizer
    _ACCESS_TOKEN_EXPIRY: ClassVar[timedelta] = timedelta(minutes=15)
    _REFRESH_TOKEN_EXPIRY: ClassVar[timedelta] = timedelta(hours=48)

    def _create_access_token(
        self,
        user_id: int,
    ) -> str:
        now = datetime.now(UTC)
        return self.tokenizer.encode(
            TokenClaims(
                sub=str(user_id),
                exp=now + self._ACCESS_TOKEN_EXPIRY,
                iat=now,
                jti=secrets.token_urlsafe(16),
                iss="orderly:login",
                aud="orderly",
                typ=TokenType.ACCESS,
            )
        ).decode("ascii")

    def _create_refresh_token(
        self,
        user_id: int,
        family_id: uuid.UUID,
    ) -> tuple[str, RefreshToken]:
        now = datetime.now(UTC)
        raw_token = self.tokenizer.encode(
            TokenClaims(
                sub=str(user_id),
                exp=now + self._REFRESH_TOKEN_EXPIRY,
                iat=now,
                jti=secrets.token_urlsafe(32),
                iss="orderly:login",
                aud="orderly:login",
                typ=TokenType.REFRESH,
                family_id=family_id,
            )
        ).decode("ascii")

        token_record = RefreshToken(
            user_id=user_id,
            token_hash=self.hasher.hash_token(raw_token).encode("utf-8"),
            family_id=family_id,
            is_used=False,
        )

        return raw_token, token_record

    # TODO: maybe later we support several login modes for apis
    async def token_login(self, email: str, password: str) -> LoginTokenResponse:
        # TODO: security including attempts, suspisous, trusted, captcha
        user = await self.user_repository.get_by_email(email)

        # The hasher should use a precomputed dummy hash when
        # the user does not exist to reduce timing differences.
        password_hash = user.password if user is not None else self.hasher.dummy_hash
        password_valid = self.hasher.verify(password, password_hash)

        if user is None or not password_valid:
            raise WrongCredentialsError()

        if not user.is_active or not user.is_email_verified:
            raise WrongCredentialsError()

        family_id = uuid.uuid4()

        access_token = self._create_access_token(user.id)
        refresh_token, refresh_token_model = self._create_refresh_token(
            user.id,
            family_id,
        )

        await self.refresh_token_repository.save(refresh_token_model)
        await self.refresh_token_repository.session.commit()

        return LoginTokenResponse(access=access_token, refresh=refresh_token)

    async def refresh_token(self, raw_token: str) -> LoginTokenResponse:
        try:
            claims = self.tokenizer.decode(raw_token)
        except Exception as exc:
            raise InvalidRefreshTokenError() from exc

        now = datetime.now(UTC)

        # Validate all refresh-token claims before using them.
        if claims.typ != TokenType.REFRESH:
            raise InvalidRefreshTokenError()

        if claims.iss != "orderly:login":
            raise InvalidRefreshTokenError()

        if claims.aud != "orderly:login":
            raise InvalidRefreshTokenError()

        if claims.exp <= now:
            raise InvalidRefreshTokenError()

        if claims.iat > now:
            raise InvalidRefreshTokenError()

        if claims.family_id is None:
            raise InvalidRefreshTokenError()

        if not claims.sub.isdecimal():
            raise InvalidRefreshTokenError()

        user_id = int(claims.sub)

        token_hash = self.hasher.hash_token(raw_token).encode("utf-8")

        # This lookup should lock the row for the duration of the transaction.
        record = await self.refresh_token_repository.get_by_hash_for_update(token_hash)

        if record is None:
            raise InvalidRefreshTokenError()

        # The signed claims must match the stored record.
        if record.user_id != user_id:
            raise InvalidRefreshTokenError()

        if record.family_id != claims.family_id:
            raise InvalidRefreshTokenError()

        if record.is_used:
            await self.refresh_token_repository.delete_family(claims.family_id)
            await self.refresh_token_repository.session.commit()
            raise InvalidRefreshTokenError()

        # Ensure the account is still allowed to authenticate.
        user = await self.user_repository.get(user_id)

        if user is None or not user.is_active or not user.is_email_verified:
            raise InvalidRefreshTokenError()

        # Consume the old token and create its replacement in the same
        # transaction. The repository must enforce single-use atomically.
        await self.refresh_token_repository.mark_used(record)

        access_token = self._create_access_token(user_id)

        new_refresh_token, new_record = self._create_refresh_token(
            user_id=user_id,
            family_id=claims.family_id,
        )

        await self.refresh_token_repository.save(new_record)
        await self.refresh_token_repository.session.commit()

        return LoginTokenResponse(
            access=access_token,
            refresh=new_refresh_token,
        )

    async def get_token_user(self, token: str) -> UserAccount:
        now = datetime.now(UTC)

        try:
            claims = self.tokenizer.decode(token)
        except Exception as exc:
            raise InvalidTokenError() from exc

        # Validate token type and required claims.
        if claims.typ != TokenType.ACCESS:
            raise InvalidTokenError()

        if claims.iss != "orderly:login":
            raise InvalidTokenError()

        if claims.aud != "orderly":
            raise InvalidTokenError()

        if claims.exp <= now:
            raise InvalidTokenError()

        if claims.iat > now:
            raise InvalidTokenError()

        # Reject malformed subjects.
        if not claims.sub.isdecimal():
            raise InvalidTokenError()

        if claims.exp - claims.iat > self._ACCESS_TOKEN_EXPIRY:
            raise InvalidTokenError()

        if not claims.jti:
            raise InvalidTokenError()

        user_id = int(claims.sub)

        # Load the account and enforce current account status.
        user = await self.user_repository.get(user_id)

        if user is None or not user.is_active or not user.is_email_verified:
            raise AccountLockedError()

        return user


class AuthorizationService:
    def __init__(
        self,
        user_repository: UserRepository,
        permission_repository: UserPermissionsRepository,
    ) -> None:
        self.user_repository = user_repository
        self.permission_repository: UserPermissionsRepository

    async def has_any_permission(
        self,
        user: UserAccount,
        permissions: tuple[str, ...],
    ) -> bool:
        if user.is_admin:
            return True

        user_permissions = {permission.perm_code for permission in user.permissions}
        return not user_permissions.isdisjoint(permissions)

    async def has_permission(
        self,
        user: UserAccount,
        perm_code: str,
    ) -> bool:
        if user.is_admin:
            return True

        return any(permission.perm_code == perm_code for permission in user.permissions)


@dataclass
class UserService:
    user_repository: UserRepository
    hasher: Hasher
    otp_service: OTPService

    async def register_user(
        self,
        register_request: RegisterUserRequest,
    ) -> UserAccount:
        duplicates = await self.user_repository.get_existing_fields(
            email=UserAccount.email == register_request.email,
            username=UserAccount.username == register_request.username,
        )

        if "email" in duplicates:
            raise UserAlreadyRegisteredError(email=register_request.email)

        if "username" in duplicates:
            raise UserAlreadyRegisteredError(username=register_request.username)

        user = UserAccount(
            **register_request.model_dump(exclude={"password"}),
            password=self.hasher.hash(register_request.password.get_secret_value()),
        )

        await self.user_repository.save(user)
        await self.otp_service.generate_and_send(user.id, UserContactInfo.model_validate(user))
        return user

    async def resend_otp(self, email: str) -> None:
        user = await self.user_repository.get_by_email(email)
        if user is None:
            logger.info(
                "OTP resend skipped",
                extra={"reason": "account_not_found"},
            )
            return None  #  keep emails private with silent fails but maybe we should log the case
        await self.otp_service.generate_and_send(user.id, UserContactInfo.model_validate(user))

    async def verify_user_email(self, email: str, code: str) -> bool:
        user = await self.user_repository.get_by_email(email)
        if not user:
            logger.info(
                "OTP email check for no user",
                extra={"reason": "account_not_found"},
            )
            return False

        if user.is_email_verified:
            logger.info(
                "OTP email check for already active user",
                extra={"reason": "account_not_found"},
            )
            return False

        otp_check = await self.otp_service.check_otp(user.id, code)
        if not otp_check:
            raise OTPCodeInvalidError()

        user.is_email_verified = True
        await self.user_repository.session.commit()
        return True
