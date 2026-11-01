"""App shell: health check, CORS, and startup."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.db.database import get_session
from app.main import app


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_every_origin(client: TestClient) -> None:
    frontend = client.get("/health", headers={"Origin": "http://localhost:3000"})
    other = client.get("/health", headers={"Origin": "https://example.com"})

    assert frontend.headers["access-control-allow-origin"] == "*"
    assert other.headers["access-control-allow-origin"] == "*"
    assert frontend.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_echoes_the_request_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_startup_initialises_the_database(mock_session) -> None:
    async def _get_session():
        yield mock_session

    app.dependency_overrides[get_session] = _get_session
    try:
        with (
            patch("app.main.init_db", new_callable=AsyncMock) as init_db,
            TestClient(app) as test_client,
        ):
            response = test_client.get("/health")
        init_db.assert_awaited()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_docs_are_served(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
