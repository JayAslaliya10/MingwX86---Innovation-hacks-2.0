from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.auth.auth0 import verify_token, get_current_user
from backend.database.connection import get_db
from backend.database.models import User
from backend.database.schemas import ChatMessage

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/")
async def chat_http(
    body: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HTTP fallback for chat (non-streaming)."""
    from backend.agent.chatbot import run_agent
    response = await run_agent(body.message, current_user, db, session_id=body.session_id)
    return {"response": response, "session_id": body.session_id}


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket endpoint for streaming agentic chat responses."""
    await websocket.accept()
    current_user = None

    try:
        # First message must be auth token
        auth_msg = await websocket.receive_json()
        token = auth_msg.get("token")
        if not token:
            await websocket.send_json({"error": "Token required"})
            await websocket.close()
            return

        # Verify token manually (can't use Depends in WebSocket)
        from fastapi.security import HTTPAuthorizationCredentials
        from backend.auth.auth0 import verify_token as _verify
        try:
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            payload = await _verify(creds)
            from backend.database.models import User
            current_user = db.query(User).filter(User.auth0_id == payload.get("sub")).first()
        except Exception:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close()
            return

        await websocket.send_json({"status": "connected", "user": current_user.full_name})

        from backend.agent.chatbot import run_agent_streaming
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id")

            async for chunk in run_agent_streaming(message, current_user, db, session_id):
                await websocket.send_json({"chunk": chunk})
            await websocket.send_json({"done": True})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
