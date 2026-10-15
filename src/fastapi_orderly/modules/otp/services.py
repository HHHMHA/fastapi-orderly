from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi_orderly.core.config import Settings
from fastapi_orderly.modules.auth.dtos import UserContactInfo
from fastapi_orderly.modules.auth.hasher import Hasher
from fastapi_orderly.modules.notifications.services import NotificationService
from fastapi_orderly.modules.otp.models import OneTimePassword
from fastapi_orderly.modules.otp.notifications import OTPNotification
from fastapi_orderly.modules.otp.repositories import OTPRepository
from fastapi_orderly.shared.utils import get_random_string


@dataclass
class OTPService:
    otp_repository: OTPRepository
    hasher: Hasher
    settings: Settings
    notification_service: NotificationService

    async def generate_otp(self, user_id: int) -> str:
        code = get_random_string(self.settings.auth.otp_length, symbols=False)
        code_hash = self.hasher.hash(code)
        expires_at = datetime.now(UTC) + timedelta(
            seconds=self.settings.auth.otp_expire_time_seconds
        )
        await self.otp_repository.get_or_merge(
            OneTimePassword.user_id == user_id,
            handler=lambda: OneTimePassword(
                user_id=user_id,
                code_hash=code_hash,
                expires_at=expires_at,
            ),
        )
        await self.otp_repository.session.commit()

        return code

    async def send_otp(self, receipent: UserContactInfo, code: str) -> None:
        otp_notification = OTPNotification(
            users=[receipent],
            context={
                "code": code,
            },
        )
        await self.notification_service.dispatch(notification=otp_notification)

    async def generate_and_send(self, user_id: int, receipent: UserContactInfo) -> None:
        code = await self.generate_otp(user_id)
        await self.send_otp(receipent=receipent, code=code)
