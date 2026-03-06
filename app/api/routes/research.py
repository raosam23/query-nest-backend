"""API routes for initiating and retrieving research sessions."""

import uuid
from app.api.dependencies import get_current_user
from app.db.database import get_session
from app.db.models import User, SessionStatus
from app.services.research_service import create_research_session, get_research_session, run_research_graph, get_research_sources
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

class ResearchRequest(BaseModel):
    """Request model for starting a research session."""
    query: str = Field(description='The query given by the user that has to be forwarded to the agent')

class ResearchResponse(BaseModel):
    """Response model representing a research session."""
    id: uuid.UUID = Field(description='The id of the research session')
    query: str = Field(description='The research query')
    status: SessionStatus = Field(description='Current status of the research session')
    final_report: Optional[str] = Field(description='Final compiled report, available when status is DONE', default=None)
    created_at: Optional[datetime] = Field(description='Timestamp when the session was created', default=None)

class SourceResponse(BaseModel):
    """Response model representing an external source."""
    id: uuid.UUID = Field(description='The id of the Source')
    url: Optional[str] = Field(description='The link/url of the source that the search agent have searched from', default=None)
    title: Optional[str] = Field(description='The title of the source', default=None)
    snippet: Optional[str] = Field(description='A snipped of the content from the source', default=None)
    credibility_score: Optional[float] = Field(description='The score given by the agent to show how credible is the source', default=None)

router = APIRouter()

@router.post('/', response_model=ResearchResponse)
async def research(research_request: ResearchRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Initiates a new research session and runs it in the background."""
    research_response = await create_research_session(research_request.query, current_user, session)
    background_tasks.add_task(run_research_graph, str(research_response.id))
    return research_response

@router.get('/{session_id}', response_model=ResearchResponse)
async def get_research(session_id: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Retrieves the status and details of a specific research session."""
    research_session = await get_research_session(session_id, current_user, session)
    return research_session

@router.get('/{session_id}/sources', response_model=List[SourceResponse])
async def get_sources(session_id: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Retrieves the list of external sources consulted during a research session."""
    sources = await get_research_sources(session_id, current_user, session)
    return sources
