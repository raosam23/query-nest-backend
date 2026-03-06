"""Service module for retrieving and deleting users' research history."""

from app.db.models import ResearchSession, User
from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List 

async def get_all_sessions(current_user: User, session: AsyncSession) -> List[ResearchSession]:
    """Retrieves all past research sessions belonging to a given user."""
    query_res = await session.execute(select(ResearchSession).where(ResearchSession.user_id == current_user.id).order_by(desc(ResearchSession.created_at)))
    research_sessions = query_res.scalars().all()
    return research_sessions

async def delete_session(session_id: str, current_user: User, session:AsyncSession):
    """Deletes a user's specific research session by ID."""
    query_res = await session.execute(select(ResearchSession).where(ResearchSession.user_id == current_user.id, ResearchSession.id == session_id))
    research_sessions = query_res.scalars().first()
    if not research_sessions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')
    await session.delete(research_sessions)
    await session.commit()
    return {'status': status.HTTP_200_OK, 'msg': 'sessions deleted succesfully'}