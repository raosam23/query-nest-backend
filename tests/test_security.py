"""Password hashing and JWT create / decode."""

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_verifies_and_uses_a_salt() -> None:
    hashed = hash_password("correct horse")
    other = hash_password("correct horse")

    assert hashed != "correct horse"
    assert hashed.startswith("$2")
    assert hashed != other
    assert verify_password("correct horse", hashed) is True
    assert verify_password("wrong horse", hashed) is False


def test_create_access_token_signs_the_subject_and_expiry() -> None:
    before = datetime.now(timezone.utc)
    token = create_access_token("user-123")
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

    assert payload["sub"] == "user-123"
    expires = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert expires > before
    assert expires <= before + timedelta(minutes=int(settings.JWT_EXPIRE_MINUTES) + 1)


def test_decode_access_token_returns_the_subject() -> None:
    token = create_access_token("user-123")

    assert decode_access_token(token) == "user-123"


def test_decode_access_token_rejects_a_tampered_token() -> None:
    token = create_access_token("user-123") + "x"

    assert decode_access_token(token) is None


def test_decode_access_token_rejects_a_token_signed_with_another_secret() -> None:
    token = jwt.encode({"sub": "user-123"}, "other-secret", algorithm=settings.JWT_ALGORITHM)

    assert decode_access_token(token) is None


def test_decode_access_token_rejects_an_expired_token() -> None:
    token = jwt.encode(
        {"sub": "user-123", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    assert decode_access_token(token) is None


def test_decode_access_token_returns_none_when_the_subject_is_missing() -> None:
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    assert decode_access_token(token) is None


def test_decode_access_token_rejects_garbage() -> None:
    assert decode_access_token("not-a-jwt") is None
