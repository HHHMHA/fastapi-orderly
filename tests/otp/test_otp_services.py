from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.dtos import UserContactInfo
from fastapi_orderly.modules.notifications.services import NotificationService
from fastapi_orderly.modules.otp.errors import OTPRateLimitError
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

    @pytest.mark.asyncio
    async def test_send_otp_rate_limited(
        self,
        otp_service: OTPService,
    ) -> None:
        recipient = UserContactInfo(
            email="recipient@example.com",
            username="test",
        )

        await otp_service.send_otp(receipent=recipient, code="123456")

        with pytest.raises(OTPRateLimitError):
            await otp_service.send_otp(receipent=recipient, code="654321")

    @pytest.mark.asyncio
    async def test_send_otp_after_rate_limit_expires(
        self,
        otp_service: OTPService,
        notification_service: NotificationService,
    ) -> None:
        recipient = UserContactInfo(
            email="recipient@example.com",
            username="test",
        )

        dispatch = AsyncMock(wraps=notification_service.dispatch)
        otp_service.notification_service.dispatch = dispatch

        key = f"otp:rate-limit:{recipient.username}"

        await otp_service.send_otp(receipent=recipient, code="123456")

        with pytest.raises(OTPRateLimitError):
            await otp_service.send_otp(receipent=recipient, code="654321")

        # Simulate the rate-limit TTL expiring without waiting 60 seconds.
        await otp_service.redis.delete(key)

        await otp_service.send_otp(receipent=recipient, code="654321")

        assert dispatch.await_count == 2

    @pytest.mark.asyncio
    async def test_send_otp_sets_rate_limit_ttl(
        self,
        otp_service: OTPService,
    ) -> None:
        recipient = UserContactInfo(
            email="recipient@example.com",
            username="test",
        )

        redis_set = AsyncMock(return_value=True)
        otp_service.redis.set = redis_set

        await otp_service.send_otp(
            receipent=recipient,
            code="123456",
            otp_rate_limit_seconds=60,
        )

        redis_set.assert_awaited_once_with(
            f"otp:rate-limit:{recipient.username}",
            "1",
            nx=True,
            ex=60,
        )

    @pytest.mark.asyncio
    async def test_check_otp_valid_code(
        self,
        otp_service: OTPService,
        user: UserAccount,
        mocker: MockerFixture,
    ) -> None:
        spy = mocker.spy(otp_service.hasher, "verify")

        code = await otp_service.generate_otp(user.id)

        result = await otp_service.check_otp(
            user_id=user.id,
            code=code,
        )

        assert result is True
        spy.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_otp_invalid_code(
        self,
        otp_service: OTPService,
        user: UserAccount,
    ) -> None:
        await otp_service.generate_otp(user.id)

        result = await otp_service.check_otp(
            user_id=user.id,
            code="000000",
        )

        assert result is False

        otp = await otp_service.otp_repository.first(
            OneTimePassword.user_id == user.id,
        )

        assert otp is not None
        assert otp.user_id == user.id

    @pytest.mark.asyncio
    async def test_check_otp_unknown_user(
        self,
        otp_service: OTPService,
    ) -> None:
        result = await otp_service.check_otp(
            user_id=999999999,
            code="123456",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_otp_cannot_be_reused(
        self,
        otp_service: OTPService,
        user: UserAccount,
    ) -> None:
        code = await otp_service.generate_otp(user.id)

        first_result = await otp_service.check_otp(
            user_id=user.id,
            code=code,
        )
        second_result = await otp_service.check_otp(
            user_id=user.id,
            code=code,
        )

        assert first_result is True
        assert second_result is False
