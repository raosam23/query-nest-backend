import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlmodel import Field, Relationship, SQLModel
from typing import List, Optional
from sqlalchemy import Column, DateTime


class SessionStatus(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    DONE = 'done'
    FAILED = 'failed'

class AgentStatus(str, Enum):
    RUNNING = 'running'
    DONE = 'done'
    FAILED = 'failed'

class User(SQLModel, table=True):
    __tablename__ = 'user'

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))
    sessions: List['ResearchSession'] = Relationship(back_populates='user')

class ResearchSession(SQLModel, table=True):
    __tablename__ = 'research_session'
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key='user.id')
    query: str
    status: SessionStatus = SessionStatus.PENDING
    final_report: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))
    completed_at: Optional[datetime] = None
    user: User = Relationship(back_populates='sessions')
    agent_logs: List['AgentLog'] = Relationship(back_populates='session')
    sources: List['Source'] = Relationship(back_populates='session')

class AgentLog(SQLModel, table=True):
    __tablename__ = 'agent_log'

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key='research_session.id')
    agent_name: str
    status: AgentStatus = AgentStatus.RUNNING
    output: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True)))
    completed_at: Optional[datetime] = None
    session: ResearchSession = Relationship(back_populates='agent_logs')

class Source(SQLModel, table=True):
    __tablename__ = 'source'

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key='research_session.id')
    url: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    credibility_score: Optional[float] = None
    session: ResearchSession = Relationship(back_populates='sources')
