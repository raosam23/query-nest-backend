from app.db.database import get_session
from app.services.auth_service import login_user, register_user
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

class AuthRequest(BaseModel):
    email: str = Field(description='User email')
    password: str = Field(description='User password')

class LoginResponse(BaseModel):
    access_token: str = Field(description='JWT access token')
    token_type: str = Field(description='Type of the token')

class RegisterResponse(BaseModel):
    message: str = Field(description='Registration success message')
    email: str = Field(description='Registered user email')

router = APIRouter()

@router.post('/register', response_model=RegisterResponse)
async def register(auth_request: AuthRequest, session: AsyncSession = Depends(get_session)):
    user = await register_user(auth_request.email, auth_request.password, session)
    return RegisterResponse(message='Account created successfully', email=user.email)

@router.post('/login', response_model=LoginResponse)
async def login(auth_request: AuthRequest, session: AsyncSession = Depends(get_session)):
    auth_token = await login_user(auth_request.email, auth_request.password, session)
    return LoginResponse(access_token=auth_token, token_type='bearer')