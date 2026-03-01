import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.api.dependencies import get_current_user
from app.services.research_service import create_research_session, get_research_session
from app.db.models import User, ResearchSession, SessionStatus
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ResearchRequest(BaseModel):
    query: str = Field(description='The query given by the user that has to be forwarded to the agent')

class ResearchResponse(BaseModel):
    id: uuid.UUID = Field(description='The id of the research session')
    query: str = Field(description='The research query')
    status: SessionStatus = Field(description='Current status of the research session')
    final_report: Optional[str] = Field(description='Final compiled report, available when status is DONE', default=None)
    created_at: Optional[datetime] = Field(description='Timestamp when the session was created', default=None)

router = APIRouter()

@router.post('/', response_model=ResearchResponse)
async def research(research_request: ResearchRequest, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    research_response = await create_research_session(research_request.query, current_user, session)
    return research_response

@router.get('/{session_id}', response_model=ResearchResponse)
async def get_research(session_id: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    research_session = await get_research_session(session_id, current_user, session)
    return research_session