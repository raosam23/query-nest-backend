from app.agents.state import ResearchState
from app.graph.builder import build_graph
from app.db.models import ResearchSession, SessionStatus, User
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

async def create_research_session(query: str, current_user: User, session: AsyncSession) -> ResearchSession:
    research_session = ResearchSession(user_id=current_user.id, query=query, status=SessionStatus.PENDING)
    graph = build_graph()
    init_state: ResearchState = {
        'query': query,
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Research pipeline failed: {exc}')
    finally:
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