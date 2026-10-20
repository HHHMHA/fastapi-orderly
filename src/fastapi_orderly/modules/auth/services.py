from dataclasses import dataclass

from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.core.loggers import logger
from fastapi_orderly.modules.auth.dtos import RegisterUserRequest, UserContactInfo
from fastapi_orderly.modules.auth.errors import UserAlreadyRegisteredError
from fastapi_orderly.modules.auth.hasher import Hasher
from fastapi_orderly.modules.auth.repositories import (
    # RefreshTokenRepository,
    # UserPermissionsRepository,
    UserRepository,
)
from fastapi_orderly.modules.otp.errors import OTPCodeInvalidError
from fastapi_orderly.modules.otp.services import OTPService

# class AuthenticationService:
#     def __init__(
#         self,
#         user_repository: UserRepository,
#         refresh_token_repository: RefreshTokenRepository,
#     ) -> None:
#         self.user_repository = user_repository
#         self.refresh_token_repository = refresh_token_repository
#
#
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
