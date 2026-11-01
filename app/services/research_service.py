"""Service module for handling research logic, orchestrating graphs, and managing data."""

from app.agents.state import ResearchState
from app.agents.supervisor import GIVE_UP_REPORTS
from app.core.stream import stream_manager
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
    stream_manager.create_queue(str(research_session.id))
    return research_session


async def run_research_graph(session_id: str):
    """Runs the LangGraph research pipeline for a given session ID."""
    research_session = None
    completion = {"type": "pipeline_completed", "status": SessionStatus.FAILED.value}
    try:
        async with async_session() as session:
            research_session_res = await session.execute(
                select(ResearchSession).where(ResearchSession.id == session_id)
            )
            research_session = research_session_res.scalars().first()
            if research_session is None:
                completion["error"] = "session not found"
                print(f"Research session not found: {session_id}")
                return None

            graph = build_graph()
            init_state: ResearchState = {
                "query": research_session.query,
                "search_results": [],
                "key_claims": [],
                "fact_check_report": {},
                "final_report": "",
                "next": "",
                "session_id": str(research_session.id),
                "db_session": session,
                "search_attempts": 0,
                "summarizer_attempts": 0,
            }
            research_session.status = SessionStatus.RUNNING
            session.add(research_session)
            await session.commit()
            await session.refresh(research_session)
            graph_result = await graph.ainvoke(init_state)
            report = graph_result.get("final_report") or ""
            # Give-up reports end the graph without an error key. They are still failures.
            failed = bool(graph_result.get("error")) or report in GIVE_UP_REPORTS
            research_session.status = SessionStatus.FAILED if failed else SessionStatus.DONE
            research_session.final_report = graph_result.get("final_report")
            research_session.completed_at = datetime.now(timezone.utc)
            session.add(research_session)
            await session.commit()
            await session.refresh(research_session)
            completion = {
                "type": "pipeline_completed",
                "status": research_session.status.value,
            }
            if failed:
                completion["error"] = report[:300] or "research pipeline failed"
    except Exception as exc:
        completion["error"] = str(exc)[:300] or "research pipeline failed"
        print(f"Research pipeline failed: {exc}")
        if research_session is not None:
            research_session.status = SessionStatus.FAILED
            research_session.completed_at = datetime.now(timezone.utc)
            try:
                async with async_session() as session:
                    session.add(research_session)
                    await session.commit()
            except Exception as persist_exc:
                print(f"Could not persist failed research status: {persist_exc}")
    finally:
        try:
            await stream_manager.push(session_id, completion)
        except Exception as stream_exc:
            print(f"Could not publish research completion: {stream_exc}")
    return research_session


async def get_research_session(session_id: str, current_user: User, session: AsyncSession) -> ResearchSession:
    """Retrieves the details of a specific research session."""
    research_session_res = await session.execute(
        select(ResearchSession).where(ResearchSession.id == session_id, ResearchSession.user_id == current_user.id)
    )
    research_session = research_session_res.scalars().first()
    if not research_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return research_session


async def get_research_sources(session_id: str, current_user: User, session: AsyncSession) -> Sequence[Source]:
    """Retrieves the external sources gathered for a specific research session."""
    await get_research_session(session_id, current_user, session)
    sources_res = await session.execute(select(Source).where(Source.session_id == session_id))
    sources = sources_res.scalars().all()
    return sources
