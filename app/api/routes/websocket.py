import asyncio
from app.core.stream import stream_manager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket('/research/{session_id}/stream')
async def research_stream(session_id: str, websocket: WebSocket):
    await websocket.accept()
    stream_manager.create_queue(session_id)
    queue: asyncio.Queue | None = stream_manager.get_queue(session_id)
    if queue is None:
        await websocket.close()
        return
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
            if (message.get('status') == 'failed') or (message.get('agent') == 'writer_agent' and message.get('status') == 'done'):
                break
    except WebSocketDisconnect:
        pass
    finally:
        stream_manager.remove_queue(session_id)
        await websocket.close()
