# TODO:Langgraph side of things will be done later
from app.db.models import ResearchSession, SessionStatus, User
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

async def create_research_session(query: str, current_user: User, session: AsyncSession) -> ResearchSession:
    research_session = ResearchSession(user_id=current_user.id, query=query, status=SessionStatus.PENDING)
    session.add(research_session)
    await session.commit()
    await session.refresh(research_session)
    return research_session

async def get_research_session(session_id: str, current_user: User, session: AsyncSession) -> ResearchSession:
    research_session_res = await session.execute(select(ResearchSession).where(ResearchSession.id == session_id, ResearchSession.user_id == current_user.id))
    research_session = research_session_res.scalars().first()
    if not research_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')
    return research_session