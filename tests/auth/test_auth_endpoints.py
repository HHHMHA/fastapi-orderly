from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orderly.core.config import get_settings
from fastapi_orderly.core.db.registry import UserAccount
from fastapi_orderly.modules.auth.deps import get_refresh_token_repository, get_tokenizer
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


class TestTokenLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        user: UserAccount,
    ) -> None:
        response = await client.post(
            "/v1/auth/token",
            data={
                "username": user.email,
                "password": "test",
            },
        )

        assert response.status_code == 400, response.text

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        active_user: UserAccount,
    ) -> None:
        response = await client.post(
            "/v1/auth/token",
            data={
                "username": active_user.email,
                "password": "test",
            },
        )

        assert response.status_code == 201, response.text

        data = response.json()
        assert data["access"]
        assert data["refresh"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        active_user: UserAccount,
    ) -> None:
        response = await client.post(
            "/v1/auth/token",
            data={
                "username": active_user.email,
                "password": "wrong-password",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/token",
            data={
                "username": "nonexistent",
                "password": "secure-password",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_missing_username(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/token",
            data={"password": "secure-password"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/token",
            data={"username": "newuser"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_empty_credentials(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post("/v1/auth/token", data={})

        assert response.status_code == 422


class TestReadCurrentUserEndpoint:
    @pytest.mark.asyncio
    async def test_read_current_user_success(
        self,
        authenticated_client: AsyncClient,
        active_user: UserAccount,
    ) -> None:
        response = await authenticated_client.get("/v1/auth/me")

        assert response.status_code == 200, response.text

        data = response.json()
        assert data["username"] == active_user.username
        assert data["email"] == active_user.email
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_read_current_user_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.get("/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_read_current_user_invalid_token(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestRefreshTokenEndpoint:
    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        client: AsyncClient,
        active_user: UserAccount,
    ) -> None:
        tokenizer = get_tokenizer(settings=get_settings())
        login_response = await client.post(
            "/v1/auth/token",
            data={
                "username": active_user.email,
                "password": "test",
            },
        )

        assert login_response.status_code == 201, login_response.text

        refresh_token = login_response.json()["refresh"]
        old_claims = tokenizer.decode(refresh_token)

        response = await client.post(
            "/v1/auth/token/refresh",
            params={"refresh_token": refresh_token},
        )

        assert response.status_code == 201, response.text

        data = response.json()
        assert data["access"]
        assert data["refresh"]

        new_claims = tokenizer.decode(data["refresh"])
        assert new_claims.family_id == old_claims.family_id
        assert new_claims.jti != old_claims.jti

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/token/refresh",
            params={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_missing(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post("/v1/auth/token/refresh")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_refresh_token_reuse(
        self,
        client: AsyncClient,
        active_user: UserAccount,
        no_app_db_session: AsyncSession,
    ) -> None:
        login_response = await client.post(
            "/v1/auth/token",
            data={
                "username": active_user.email,
                "password": "test",
            },
        )

        refresh_token = login_response.json()["refresh"]

        first_response = await client.post(
            "/v1/auth/token/refresh",
            params={"refresh_token": refresh_token},
        )

        assert first_response.status_code == 201

        second_response = await client.post(
            "/v1/auth/token/refresh",
            params={"refresh_token": refresh_token},
        )

        assert second_response.status_code == 401

        refresh_token_repository = get_refresh_token_repository(session=no_app_db_session)
        assert await refresh_token_repository.count() == 0


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        client: AsyncClient,
        active_user: UserAccount,
        no_app_db_session: AsyncSession,
    ) -> None:
        login_response = await client.post(
            "/v1/auth/token",
            data={
                "username": active_user.email,
                "password": "test",
            },
        )

        refresh_token = login_response.json()["refresh"]

        response = await client.post(
            "/v1/auth/token/logout",
            params={"refresh_token": refresh_token},
        )

        assert response.status_code == 200

        refresh_token_repository = get_refresh_token_repository(session=no_app_db_session)
        assert await refresh_token_repository.count() == 0

    @pytest.mark.asyncio
    async def test_logout_invalid_refresh_token(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/v1/auth/token/logout",
            params={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_missing_refresh_token(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post("/v1/auth/token/logout")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_logout_all_success(
        self, authenticated_client: AsyncClient, no_app_db_session: AsyncSession
    ) -> None:
        response = await authenticated_client.post(
            "/v1/auth/token/logout/all",
        )

        assert response.status_code == 200

        refresh_token_repository = get_refresh_token_repository(session=no_app_db_session)
        assert await refresh_token_repository.count() == 0

    @pytest.mark.asyncio
    async def test_logout_all_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.post("/v1/auth/token/logout/all")

        assert response.status_code == 401
