"""
This module contains all the routes for authentication purposes, i.e., for signup and login
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.auth_service import login_user, register_user


class AuthRequest(BaseModel):
    """Request model for user authentication."""

    email: str = Field(description="User email")
    password: str = Field(description="User password")


class LoginResponse(BaseModel):
    """Response model for a successful user login."""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(description="Type of the token")


class RegisterResponse(BaseModel):
    """Response model for a successful user registration."""

    message: str = Field(description="Registration success message")
    email: str = Field(description="Registered user email")


router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register(
    auth_request: AuthRequest, session: AsyncSession = Depends(get_session)
):
    """Register a new user account."""
    user = await register_user(auth_request.email, auth_request.password, session)
    return RegisterResponse(message="Account created successfully", email=user.email)


@router.post("/login", response_model=LoginResponse)
async def login(
    auth_request: AuthRequest, session: AsyncSession = Depends(get_session)
):
    """Authenticate a user and return an access token."""
    auth_token = await login_user(auth_request.email, auth_request.password, session)
    return LoginResponse(access_token=auth_token, token_type="bearer")
