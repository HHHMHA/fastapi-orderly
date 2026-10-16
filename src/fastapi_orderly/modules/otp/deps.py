from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.config import Settings, get_settings
from fastapi_orderly.core.db.session import get_session
from fastapi_orderly.modules.auth.hasher import Hasher, get_hasher
from fastapi_orderly.modules.notifications.deps import get_notification_service
from fastapi_orderly.modules.notifications.services import NotificationService
from fastapi_orderly.modules.otp.repositories import OTPRepository
from fastapi_orderly.modules.otp.services import OTPService


def get_otp_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> OTPRepository:
    return OTPRepository(session=session)


def get_otp_service(
    otp_repository: Annotated[OTPRepository, Depends(get_otp_repository)],
    hasher: Annotated[Hasher, Depends(get_hasher)],
    settings: Annotated[Settings, Depends(get_settings)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> OTPService:
    return OTPService(
        otp_repository=otp_repository,
        hasher=hasher,
        settings=settings,
        notification_service=notification_service,
    )
