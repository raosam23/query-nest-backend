"""Security module handling password hashing and JWT tokens."""

import bcrypt
from app.core.config import settings
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

# pwd_context = CryptContext(schemes=['bcrypt_sha256'], deprecated='auto')

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    # return pwd_context.hash(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a hashed password."""
    # return pwd_context.verify(plain_password, hashed_password)
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(user_id: str) -> str:
    """Creates a JSON Web Token (JWT) for authentication."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=int(settings.JWT_EXPIRE_MINUTES))
    to_encode = {'sub': user_id, 'exp': expire}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> str:
    """Decodes and validates a full access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload.get('sub')
    except JWTError:
        return None