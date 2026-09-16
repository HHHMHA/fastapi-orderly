import httpx
import pytest
from httpx import ASGITransport

from fastapi_orderly.main import create_app


@pytest.mark.asyncio
async def test_health() -> None:
    app = create_app()

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
    }
