"""
WebSocket routes for streaming research progress to clients.
"""

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select

from app.core.security import decode_access_token
from app.core.stream import stream_manager
from app.db.database import async_session
from app.db.models import ResearchSession

router = APIRouter()


@router.websocket("/research/{session_id}/stream")
async def research_stream(session_id: str, websocket: WebSocket):
    """
    WebSocket router method to stream research data back to the client.

    Args:
        session_id (str): The unique identifier for the research session.
        websocket (WebSocket): The active WebSocket connection for the client.
    """
    token = websocket.query_params.get("token")
    user_id = decode_access_token(token) if token else None
    if not user_id:
        await websocket.accept()
        await websocket.close(code=1008, reason="Invalid token or session access denied")
        return
    try:
        session_uuid = uuid.UUID(session_id)
        async with async_session() as db_session:
            result = await db_session.execute(select(ResearchSession).where(ResearchSession.id == session_uuid))
            research_session = result.scalars().first()
    except (ValueError, TypeError):
        research_session = None
    except Exception:
        research_session = None
    if research_session is None or str(research_session.user_id) != str(user_id):
        await websocket.accept()
        await websocket.close(code=1008, reason="Invalid token or session access denied")
        return

    await websocket.accept()
    stream_manager.add_listener(session_id)
    queue: asyncio.Queue | None = stream_manager.get_queue(session_id)
    if queue is None:
        await websocket.close()
        return
    completed = False
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
            if message.get("type") == "pipeline_completed":
                completed = True
                break
    except WebSocketDisconnect:
        pass
    finally:
        stream_manager.remove_listener(session_id)
        if completed:
            stream_manager.remove_queue(session_id)
        try:
            await websocket.close()
        except RuntimeError:
            pass
