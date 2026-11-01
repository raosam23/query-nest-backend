"""Register and login HTTP routes."""

from fastapi.testclient import TestClient

from app.core.security import decode_access_token, verify_password
from app.db.models import User
from tests.factories import make_user, scalar_result


def test_register_creates_an_account(client: TestClient, mock_session) -> None:
    mock_session.execute.return_value = scalar_result(None)

    response = client.post("/auth/register", json={"email": "ada@example.com", "password": "secret-password"})

    assert response.status_code == 200
    assert response.json() == {"message": "Account created successfully", "email": "ada@example.com"}
    created = mock_session.add.call_args.args[0]
    assert isinstance(created, User)
    assert created.email == "ada@example.com"
    assert verify_password("secret-password", created.password_hash) is True
    assert "password" not in response.json()


def test_register_rejects_a_duplicate_email(client: TestClient, mock_session) -> None:
    mock_session.execute.return_value = scalar_result(make_user(email="ada@example.com"))

    response = client.post("/auth/register", json={"email": "ada@example.com", "password": "secret-password"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Email is already registered"


def test_register_requires_a_password(client: TestClient) -> None:
    response = client.post("/auth/register", json={"email": "ada@example.com"})

    assert response.status_code == 422


def test_login_returns_a_bearer_token(client: TestClient, mock_session) -> None:
    user = make_user(password="secret-password")
    mock_session.execute.return_value = scalar_result(user)

    response = client.post("/auth/login", json={"email": user.email, "password": "secret-password"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert decode_access_token(body["access_token"]) == str(user.id)
    assert "password" not in body


def test_login_rejects_unknown_email_and_a_wrong_password(client: TestClient, mock_session) -> None:
    user = make_user(password="secret-password")
    mock_session.execute.return_value = scalar_result(None)
    missing = client.post("/auth/login", json={"email": "missing@example.com", "password": "secret-password"})

    mock_session.execute.return_value = scalar_result(user)
    wrong = client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json()["detail"] == "Invalid credentials"
    assert wrong.json()["detail"] == "Invalid credentials"
