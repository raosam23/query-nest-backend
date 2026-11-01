"""Current-user dependency through the HTTP bearer scheme."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from tests.factories import scalar_result

PROTECTED = [
    ("post", "/research/"),
    ("get", "/research/00000000-0000-0000-0000-000000000001"),
    ("get", "/research/00000000-0000-0000-0000-000000000001/sources"),
    ("get", "/history/"),
    ("delete", "/history/00000000-0000-0000-0000-000000000001"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_protected_routes_require_a_bearer_token(client: TestClient, method: str, path: str) -> None:
    kwargs = {"json": {"query": "What is nuclear fusion?"}} if method == "post" else {}
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_protected_route_rejects_a_bad_bearer_token(client: TestClient) -> None:
    response = client.get("/history/", headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_protected_route_rejects_an_unknown_user(client: TestClient, mock_session) -> None:
    token = create_access_token(str(uuid.uuid4()))
    mock_session.execute.return_value = scalar_result(None)

    response = client.get("/history/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"
