import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.services import UserService


class TestOTPResendEndPoint:
    @pytest.mark.asyncio
    async def test_resend_otp_success(self, client: AsyncClient, user: UserAccount) -> None:
        response = await client.post(
            "/v1/auth/otp/resend",
            json={"email": user.email},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_resend_otp_success_no_user(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/auth/otp/resend",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_resend_otp_invalid_email(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/auth/otp/resend",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_resend_otp_rate_limited(self, client: AsyncClient, user: UserAccount) -> None:
        payload = {"email": user.email}

        first_response = await client.post("/v1/auth/otp/resend", json=payload)
        assert first_response.status_code == 201

        second_response = await client.post("/v1/auth/otp/resend", json=payload)

        assert second_response.status_code == 429

    @pytest.mark.asyncio
    async def test_resend_otp_after_rate_limit_cleared(
        self,
        client: AsyncClient,
        redis_client: Redis,
        user: UserAccount,
    ) -> None:
        payload = {"email": user.email}
        key = "otp:rate-limit:test"

        first_response = await client.post("/v1/auth/otp/resend", json=payload)
        assert first_response.status_code == 201

        second_response = await client.post("/v1/auth/otp/resend", json=payload)
        assert second_response.status_code == 429

        await redis_client.delete(key)

        third_response = await client.post("/v1/auth/otp/resend", json=payload)
        assert third_response.status_code == 201


class TestOTPCheckEndpoint:
    @pytest.mark.asyncio
    async def test_check_otp_success(
        self,
        client: AsyncClient,
        user: UserAccount,
        user_service: UserService,
    ) -> None:
        code = await user_service.otp_service.generate_otp(user.id)

        payload = {
            "email": user.email,
            "code": code,
        }

        assert user.is_email_verified is False
        response = await client.post(
            "/v1/auth/otp/check",
            json=payload,
        )

        assert response.status_code == 200
        assert user.is_email_verified is True

    @pytest.mark.asyncio
    async def test_check_otp_invalid_code(
        self,
        client: AsyncClient,
        user: UserAccount,
        user_service: UserService,
    ) -> None:
        await user_service.otp_service.generate_otp(user.id)

        response = await client.post(
            "/v1/auth/otp/check",
            json={
                "email": user.email,
                "code": "000000",
            },
        )

        assert response.status_code == 400
        assert user.is_email_verified is False

    @pytest.mark.asyncio
    async def test_check_otp_nonexistent_user(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/otp/check",
            json={
                "email": "nonexistent@example.com",
                "code": "123456",
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_check_otp_already_verified_user(
        self,
        client: AsyncClient,
        user: UserAccount,
    ) -> None:
        user.is_email_verified = True

        response = await client.post(
            "/v1/auth/otp/check",
            json={
                "email": user.email,
                "code": "123456",
            },
        )

        assert response.status_code == 200
        user.is_email_verified = True

    @pytest.mark.asyncio
    async def test_check_otp_invalid_email(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/otp/check",
            json={
                "email": "not-an-email",
                "code": "123456",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_check_otp_missing_code(
        self,
        client: AsyncClient,
        user: UserAccount,
    ) -> None:
        response = await client.post(
            "/v1/auth/otp/check",
            json={"email": user.email},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_check_otp_missing_email(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/otp/check",
            json={"code": "123456"},
        )

        assert response.status_code == 422
