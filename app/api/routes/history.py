from app.api.dependencies import get_current_user
from app.api.routes.research import ResearchResponse
from app.db.database import get_session
from app.db.models import User
from app.services.history_service import get_all_sessions, delete_session
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

class DeleteResponse(BaseModel):
    status: int = Field(description='HTTP status of the delete research session')
    msg: str = Field(description='The message of the HTTPException')

router = APIRouter()

@router.get('/', response_model=List[ResearchResponse])
async def get_research_response(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    all_sessions = await get_all_sessions(current_user, session)
    return all_sessions

@router.delete('/{session_id}', response_model=DeleteResponse)
async def delete_research_session(session_id: str, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    delete_session_res = await delete_session(session_id, current_user, session)
    return delete_session_res