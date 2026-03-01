from app.db.models import User
from app.core.security import create_access_token, hash_password, verify_password
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select


async def register_user(email:str, password:str, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == email))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email is already registered')
    hashed_password = hash_password(password)
    new_user = User(email=email, password_hash=hashed_password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user
    
async def login_user(email:str, password:str, session: AsyncSession) -> str:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    return create_access_token(str(user.id))