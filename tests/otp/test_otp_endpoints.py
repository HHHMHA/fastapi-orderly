import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

from fastapi_orderly.core.db.registry import UserAccount


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
