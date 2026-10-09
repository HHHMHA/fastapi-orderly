from fastapi_orderly.modules.auth.dtos import RegisterUserRequest
from fastapi_orderly.modules.auth.hasher import Hasher
from fastapi_orderly.modules.auth.repositories import (
    RefreshTokenRepository,
    UserPermissionsRepository,
    UserRepository,
)


class AuthenticationService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository


class AuthorizationService:
    def __init__(
        self,
        user_repository: UserRepository,
        permission_repository: UserPermissionsRepository,
    ) -> None:
        self.user_repository = user_repository
        self.permission_repository: UserPermissionsRepository


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        hasher: Hasher,
    ) -> None:
        self.user_repository = user_repository
        self.hasher = hasher

    def register_user(
        self,
        register_request: RegisterUserRequest,
    ) -> None:
        # user = UserAccount(
        #     **register_request.model_dump(exclude={"password"}),
        #     password=self.hasher.hash(register_request.password),
        # )
        # email_service.send_verification_email(user.email)
        pass
