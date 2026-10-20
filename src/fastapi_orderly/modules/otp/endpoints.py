from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from fastapi_orderly.modules.auth.deps import get_user_service
from fastapi_orderly.modules.auth.services import UserService
from fastapi_orderly.modules.otp.dtos import OTPCheckRequest, OTPResendRequest

otp_router = APIRouter(prefix="/auth/otp")


@otp_router.post("/resend", status_code=status.HTTP_201_CREATED)
async def resend_otp(
    data: Annotated[OTPResendRequest, Body()],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await user_service.resend_otp(str(data.email))


@otp_router.post("/check", status_code=status.HTTP_200_OK)
async def check_otp(
    data: Annotated[OTPCheckRequest, Body()],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await user_service.verify_user_email(str(data.email), data.code)
