import httpx
import pytest


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
    }
