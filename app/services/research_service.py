"""Service module for handling research logic, orchestrating graphs, and managing data."""

from app.agents.state import ResearchState
from app.graph.builder import build_graph
from app.db.database import async_session
from app.db.models import ResearchSession, SessionStatus, Source, User
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Sequence

async def create_research_session(query: str, current_user: User, session: AsyncSession) -> ResearchSession:
    """Creates a new pending research session in the database."""
    research_session = ResearchSession(user_id=current_user.id, query=query, status=SessionStatus.PENDING)
    session.add(research_session)
    await session.commit()
    await session.refresh(research_session)
    return research_session

async def run_research_graph(session_id: str):
    """Runs the LangGraph research pipeline for a given session ID."""
    async with async_session() as session:
        research_session_res = await session.execute(select(ResearchSession).where(ResearchSession.id == session_id))
        research_session: ResearchSession = research_session_res.scalars().first()
        graph = build_graph()
        init_state: ResearchState = {
            'query': research_session.query,
            'search_results': [],
            'key_claims': [],
            'fact_check_report': {},
            'final_report': '',
            'next': '',
            'session_id': str(research_session.id),
            'db_session': session
        }
        research_session.status = SessionStatus.RUNNING
        session.add(research_session)
        await session.commit()
        await session.refresh(research_session)
        try:
            graph_result = await graph.ainvoke(init_state)
            research_session.status = SessionStatus.DONE
            research_session.final_report = graph_result.get('final_report')
            research_session.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            research_session.status = SessionStatus.FAILED
            research_session.completed_at = datetime.now(timezone.utc)
            print(f'Research pipeline failed {exc}')
        finally:
            session.add(research_session)
            await session.commit()
            await session.refresh(research_session)
    return research_session

async def get_research_session(session_id: str, current_user: User, session: AsyncSession) -> ResearchSession:
    """Retrieves the details of a specific research session."""
    research_session_res = await session.execute(select(ResearchSession).where(ResearchSession.id == session_id, ResearchSession.user_id == current_user.id))
    research_session = research_session_res.scalars().first()
    if not research_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found')
    return research_session

async def get_research_sources(session_id: str, current_user: User, session: AsyncSession) -> Sequence[Source]:
    """Retrieves the external sources gathered for a specific research session."""
    await get_research_session(session_id, current_user, session)
    sources_res = await session.execute(select(Source).where(Source.session_id == session_id))
    sources = sources_res.scalars().all()
    return sources
