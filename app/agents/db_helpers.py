from app.db.models import AgentLog, AgentStatus
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

async def log_agent_start(db_session: AsyncSession, session_id: str, agent_name: str) -> AgentLog:
    agent_log = AgentLog(
        session_id=session_id,
        agent_name=agent_name,
        status=AgentStatus.RUNNING
    )
    db_session.add(agent_log)
    await db_session.commit()
    await db_session.refresh(agent_log)
    return agent_log

async def update_agent_log(db_session: AsyncSession, log_id, output: str, agent_status: AgentStatus = AgentStatus.DONE) -> None:
    agent_log_res = await db_session.execute(select(AgentLog).where(AgentLog.id == log_id))
    agent_log = agent_log_res.scalars().first()
    if not agent_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent Log not found')
    agent_log.status = agent_status
    agent_log.output = output
    agent_log.completed_at = datetime.now(timezone.utc)
    db_session.add(agent_log)
    await db_session.commit()
    await db_session.refresh(agent_log)