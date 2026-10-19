from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.dtos import RegisterUserRequest
from fastapi_orderly.modules.auth.endpoints import register_user
from fastapi_orderly.modules.auth.services import UserService


class TestUserRegisterEndpoint:
    @pytest.mark.asyncio
    async def test_register_user_success(
        self,
        client: AsyncClient,
        no_app_db_session: AsyncSession,
    ) -> None:
        response = await client.post(
            "/v1/auth/register",
            json={
                "username": "newuser",
                "email": "NewUser@example.com",
                "password": "secure-password",
            },
        )

        assert response.status_code == 201, response.text

        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "password" not in data
        assert data["is_email_verified"] is False

        result = await no_app_db_session.execute(
            select(UserAccount).where(UserAccount.email == "newuser@example.com")
        )
        user = result.scalar_one()

        assert user.username == "newuser"
        assert user.password == "secure-password"

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(
        self,
        client: AsyncClient,
        user: UserAccount,
    ) -> None:
        response = await client.post(
            "/v1/auth/register",
            json={
                "username": "anotheruser",
                "email": user.email,
                "password": "secure-password",
            },
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(
        self,
        client: AsyncClient,
        user: UserAccount,
    ) -> None:
        response = await client.post(
            "/v1/auth/register",
            json={
                "username": user.username,
                "email": "another@example.com",
                "password": "secure-password",
            },
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email_and_username(
        self,
        client: AsyncClient,
        user: UserAccount,
        no_app_db_session: AsyncSession,
    ) -> None:
        response = await client.post(
            "/v1/auth/register",
            json={
                "username": user.username,
                "email": user.email,
                "password": "secure-password",
            },
        )

        assert response.status_code == 409

        result = await no_app_db_session.execute(select(func.count()).select_from(UserAccount))
        assert result.scalar_one() == 1

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/register",
            json={
                "username": "newuser",
                "email": "not-an-email",
                "password": "secure-password",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"username": "newuser"},
            {"email": "newuser@example.com"},
            {"password": "secure-password"},
            {
                "username": "newuser",
                "email": "newuser@example.com",
            },
        ],
    )
    async def test_register_user_missing_required_fields(
        self,
        client: AsyncClient,
        payload: dict[str, str],
    ) -> None:
        response = await client.post("/v1/auth/register", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            None,
            [],
            "invalid",
            123,
        ],
    )
    async def test_register_user_invalid_json_shape(
        self,
        client: AsyncClient,
        payload: object,
    ) -> None:
        response = await client.post("/v1/auth/register", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_user_malformed_json(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/register",
            content=b'{"username":',
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_user_returns_validated_response(
        self,
        user: UserAccount,
    ) -> None:
        service = AsyncMock(spec=UserService)
        service.register_user.return_value = user

        data = RegisterUserRequest(
            username=user.username,
            email=user.email,
            password=SecretStr("secure-password"),
        )

        result = await register_user(data=data, user_service=service)

        assert result.username == user.username
        assert result.email == user.email
        service.register_user.assert_awaited_once_with(data)
