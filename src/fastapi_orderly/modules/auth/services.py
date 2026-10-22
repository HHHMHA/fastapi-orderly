import secrets
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
from fastapi_orderly.modules.auth.errors import UserAlreadyRegisteredError, WrongCredentialsError
from fastapi_orderly.modules.auth.hasher import Hasher
from fastapi_orderly.modules.auth.repositories import (
    # RefreshTokenRepository,
    # UserPermissionsRepository,
    RefreshTokenRepository,
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

        now = datetime.now(UTC)
        access_jti = secrets.token_urlsafe(16)
        refresh_jti = secrets.token_urlsafe(32)
        access_token: str = self.tokenizer.encode(
            TokenClaims(
                sub=str(user.id),
                exp=now + self._ACCESS_TOKEN_EXPIRY,
                iat=now,
                jti=access_jti,
                iss="orderly:login",
                aud="orderly",
                typ=TokenType.ACCESS,
            )
        ).decode("ascii")

        refresh_token: str = self.tokenizer.encode(
            TokenClaims(
                sub=str(user.id),
                exp=now + self._REFRESH_TOKEN_EXPIRY,
                iat=now,
                jti=refresh_jti,
                iss="orderly:login",
                aud="orderly:login",
                typ=TokenType.REFRESH,
            )
        ).decode("ascii")

        refresh_token_model = RefreshToken(
            user_id=user.id, token_hash=self.hasher.hash_token(refresh_token).encode("utf-8")
        )
        await self.refresh_token_repository.save(refresh_token_model)
        await self.refresh_token_repository.session.commit()

        return LoginTokenResponse(access=access_token, refresh=refresh_token)


# class AuthorizationService:
#     def __init__(
#         self,
#         user_repository: UserRepository,
#         permission_repository: UserPermissionsRepository,
#     ) -> None:
#         self.user_repository = user_repository
#         self.permission_repository: UserPermissionsRepository


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
