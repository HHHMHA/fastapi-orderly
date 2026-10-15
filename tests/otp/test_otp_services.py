from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.dtos import UserContactInfo
from fastapi_orderly.modules.notifications.services import NotificationService
from fastapi_orderly.modules.otp.models import OneTimePassword
from fastapi_orderly.modules.otp.services import OTPService


class TestOTPService:
    @pytest.mark.asyncio
    async def test_generate_otp(
        self,
        otp_service: OTPService,
        user: UserAccount,
        no_app_db_session: AsyncSession,
    ) -> None:
        code = await otp_service.generate_otp(user.id)

        assert len(code) == get_settings().auth.otp_length

        otp = await otp_service.otp_repository.first(OneTimePassword.user_id == user.id)

        assert otp is not None
        assert otp.user_id == user.id
        assert otp.code_hash == code
        assert otp.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_generate_otp_sets_configured_expiration(
        self,
        otp_service: OTPService,
        user: UserAccount,
    ) -> None:
        before = datetime.now(UTC)

        await otp_service.generate_otp(user.id)

        after = datetime.now(UTC)

        otp = await otp_service.otp_repository.first(OneTimePassword.user_id == user.id)

        assert otp is not None

        expected_min = before + timedelta(seconds=get_settings().auth.otp_expire_time_seconds)
        expected_max = after + timedelta(seconds=get_settings().auth.otp_expire_time_seconds)

        assert expected_min <= otp.expires_at <= expected_max

    @pytest.mark.asyncio
    async def test_generate_otp_updates_existing_otp(
        self,
        otp_service: OTPService,
        user: UserAccount,
    ) -> None:
        first_code = await otp_service.generate_otp(user.id)

        first_otp = await otp_service.otp_repository.first(OneTimePassword.user_id == user.id)
        assert first_otp is not None

        first_hash = first_otp.code_hash

        second_code = await otp_service.generate_otp(user.id)

        updated_otp = await otp_service.otp_repository.first(OneTimePassword.user_id == user.id)

        assert updated_otp is not None
        assert updated_otp.id == first_otp.id
        assert updated_otp.code_hash == second_code
        assert updated_otp.code_hash != first_hash
        assert second_code != first_code

        assert await otp_service.otp_repository.count(OneTimePassword.user_id == user.id) == 1

    @pytest.mark.asyncio
    async def test_send_otp(
        self,
        otp_service: OTPService,
        notification_service: NotificationService,
    ) -> None:
        recipient = UserContactInfo(
            email="recipient@example.com",
            username="test",
        )
        code = "123456"

        dispatch = AsyncMock(
            wraps=notification_service.dispatch,
        )
        otp_service.notification_service.dispatch = dispatch

        await otp_service.send_otp(receipent=recipient, code=code)

        dispatch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_and_send(
        self,
        otp_service: OTPService,
        user: UserAccount,
        notification_service: NotificationService,
    ) -> None:
        recipient = UserContactInfo(email="recipient@example.com", username="test")

        dispatch = AsyncMock(
            wraps=notification_service.dispatch,
        )
        otp_service.notification_service.dispatch = dispatch

        await otp_service.generate_and_send(
            user_id=user.id,
            receipent=recipient,
        )

        dispatch.assert_awaited_once()

        otp = await otp_service.otp_repository.first(OneTimePassword.user_id == user.id)

        assert otp is not None
        assert otp.code_hash is not None

        assert len(otp.code_hash) == get_settings().auth.otp_length
