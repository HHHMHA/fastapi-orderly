from typing import Annotated

from fastapi import APIRouter, Body, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.deps import (
    authenticated_user,
    get_authentication_service,
    get_user_service,
)
from fastapi_orderly.modules.auth.dtos import (
    LoginTokenResponse,
    RegisterUserRequest,
    UserDetailsResponse,
)
from fastapi_orderly.modules.auth.services import AuthenticationService, UserService

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    data: Annotated[RegisterUserRequest, Body()],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserDetailsResponse:
    user = await user_service.register_user(data)
    result = UserDetailsResponse.model_validate(user)
    return result


@auth_router.post("/token", status_code=status.HTTP_201_CREATED)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    authentication_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> LoginTokenResponse:
    return await authentication_service.token_login(form_data.username, form_data.password)


@auth_router.get("/me")
async def read_users_me(
    current_user: Annotated[UserAccount, Depends(authenticated_user)],
) -> UserDetailsResponse:
    return UserDetailsResponse.model_validate(current_user)


@auth_router.post("/token/refresh", status_code=status.HTTP_201_CREATED)
async def refresh_token(
    refresh_token: str,
    authentication_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> LoginTokenResponse:
    return await authentication_service.refresh_token(refresh_token)


@auth_router.post("/token/logout/all", status_code=status.HTTP_200_OK)
async def logout_all(
    current_user: Annotated[UserAccount, Depends(authenticated_user)],
    authentication_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> None:
    return await authentication_service.logout_all(current_user.id)


@auth_router.post("/token/logout", status_code=status.HTTP_200_OK)
async def logout(
    refresh_token: str,
    authentication_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> None:
    return await authentication_service.logout(refresh_token)
