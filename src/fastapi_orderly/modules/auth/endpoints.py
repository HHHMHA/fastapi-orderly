from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from fastapi_orderly.modules.auth.deps import get_user_service
from fastapi_orderly.modules.auth.dtos import RegisterUserRequest, UserDetailsResponse
from fastapi_orderly.modules.auth.services import UserService

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    data: Annotated[RegisterUserRequest, Body()],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserDetailsResponse:
    user = await user_service.register_user(data)
    result = UserDetailsResponse.model_validate(user)
    return result
