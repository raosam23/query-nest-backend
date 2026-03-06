"""
Database helper function that logs agent updates
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.stream import stream_manager
from app.db.models import AgentLog, AgentStatus


async def log_agent_start(
    db_session: AsyncSession, session_id: str, agent_name: str
) -> AgentLog:
    """
    log_agent_start function, that creates an entry in the AgentLog and pushes the status and the agent name to the websocket aswell

    Args:
        db_session (AsyncSession): the database session
        session_id (str): the unique identifier for agent
        agent_name (str): name of the agent that is running

    Returns:
        AgentLog: instance of the AgentLog session
    """
    agent_log = AgentLog(
        session_id=uuid.UUID(session_id),
        agent_name=agent_name,
        status=AgentStatus.RUNNING,
    )
    db_session.add(agent_log)
    await db_session.commit()
    await stream_manager.push(
        session_id, {"agent": agent_name, "status": AgentStatus.RUNNING.value}
    )
    await db_session.refresh(agent_log)
    return agent_log


async def update_agent_log(
    db_session: AsyncSession,
    log_id: uuid.UUID,
    output: str,
    agent_status: AgentStatus = AgentStatus.DONE,
) -> None:
    """
    update_agent_log method updates the agent log if the log_id exists in AgentLog table and also pushes a websocket update with the same for streaming

    Args:
        db_session (AsyncSession): the database session
        log_id (uuid.UUID): the id of the AgentLog
        output (str): the output of the agent
        agent_status (AgentStatus): the status of the agent, by default it is set to DONE

    Raises:
        HTTPException: If no AgentLog entry exists with the provided `log_id`.
    """
    agent_log_res = await db_session.execute(
        select(AgentLog).where(AgentLog.id == log_id)
    )
    agent_log = agent_log_res.scalars().first()
    if not agent_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent Log not found"
        )
    agent_log.status = agent_status
    agent_log.output = output
    agent_log.completed_at = datetime.now(timezone.utc)
    db_session.add(agent_log)
    await db_session.commit()
    await stream_manager.push(
        str(agent_log.session_id),
        {
            "agent": agent_log.agent_name,
            "status": agent_log.status.value,
            "output": output,
        },
    )
    await db_session.refresh(agent_log)
