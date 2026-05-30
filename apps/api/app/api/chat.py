# ############################################################################
# AI_HEADER: MODULE_API_CHAT
# ROLE: Chat API endpoints
# DEPENDENCIES: fastapi, app.services.chat_service, app.schemas.chat
# GRACE_ANCHORS: [CREATE_THREAD_ENDPOINT, GET_THREAD_ENDPOINT, SEND_MESSAGE_ENDPOINT]
# WAVE: W-CHAT-1
# ############################################################################

# START_MODULE_CONTRACT: M-API-CHAT
# purpose: REST endpoints for chat threads and messages
# owns:
#   - apps/api/app/api/chat.py
# inputs:
#   - POST /api/chat/threads: create thread
#   - GET /api/chat/threads/{thread_id}: get thread with messages
#   - POST /api/chat/threads/{thread_id}/messages: send message
# outputs:
#   - JSON responses with thread and message data
# dependencies:
#   - M-CHAT-SERVICE
#   - M-CHAT-SCHEMA
#   - M-AUTH-TG (require_session)
# side_effects:
#   - creates threads and messages via ChatService
# invariants:
#   - all endpoints require authentication
#   - thread ownership verified by service layer
# failure_policy:
#   - 404 if thread not found
#   - 422 if validation fails
# non_goals:
#   - no rate limiting (MVP)
#   - no LLM integration (echo bot)
# END_MODULE_CONTRACT: M-API-CHAT

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.chat import MessageCreate, MessageResponse, ThreadResponse
from app.services.chat_service import ChatService
from app.services.chat_quota_service import ChatQuotaService

router = APIRouter()


# START_BLOCK: CREATE_THREAD_ENDPOINT
@router.post("/api/chat/threads")
async def create_thread(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_session),
):
    """Create new chat thread. W-CHAT-1."""
    service = ChatService(db)
    thread = await service.create_thread(current_user.id)

    return {
        "id": str(thread.id),
        "created_at": thread.created_at.isoformat(),
    }
# END_BLOCK: CREATE_THREAD_ENDPOINT


# START_BLOCK: GET_THREAD_ENDPOINT
@router.get("/api/chat/threads/{thread_id}")
async def get_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_session),
):
    """Get thread with messages. W-CHAT-1."""
    service = ChatService(db)
    thread = await service.get_thread(thread_id, current_user.id)

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = await service.get_messages(thread_id, current_user.id)

    return ThreadResponse(
        id=str(thread.id),
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        messages=[
            MessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )
# END_BLOCK: GET_THREAD_ENDPOINT


# START_BLOCK: SEND_MESSAGE_ENDPOINT
@router.post("/api/chat/threads/{thread_id}/messages")
async def send_message(
    thread_id: uuid.UUID,
    message: MessageCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_session),
):
    """Send message to thread. W-CHAT-1. MVP: echo bot."""
    service = ChatService(db)

    try:
        # Add user message
        user_message = await service.add_message(
            thread_id=thread_id,
            user_id=current_user.id,
            role="user",
            content=message.content,
        )
    except ValueError as e:
        # W-CHAT-4: Handle quota exceeded
        if "quota exceeded" in str(e).lower():
            raise HTTPException(status_code=400, detail="Chat quota exceeded")
        raise HTTPException(status_code=404, detail=str(e))

    # TODO: Generate assistant response (LLM integration)
    # For MVP, return echo
    assistant_message = await service.add_message(
        thread_id=thread_id,
        user_id=current_user.id,
        role="assistant",
        content=f"Вы сказали: {message.content}",
    )

    return {
        "user_message": MessageResponse(
            id=str(user_message.id),
            role=user_message.role,
            content=user_message.content,
            created_at=user_message.created_at.isoformat(),
        ),
        "assistant_message": MessageResponse(
            id=str(assistant_message.id),
            role=assistant_message.role,
            content=assistant_message.content,
            created_at=assistant_message.created_at.isoformat(),
        ),
    }
# END_BLOCK: SEND_MESSAGE_ENDPOINT


# START_BLOCK: GET_QUOTA_ENDPOINT
@router.get("/api/chat/quota")
async def get_quota(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_session),
):
    """
    Get user's chat quota.

    W-CHAT-4: Returns used/limit/reset_at.
    """
    service = ChatQuotaService(db)
    quota = await service.get_or_create_quota(current_user.id)

    return {
        "messages_used": quota.messages_used,
        "messages_limit": quota.messages_limit,
        "reset_at": quota.reset_at.isoformat(),
        "remaining": quota.messages_limit - quota.messages_used,
    }
# END_BLOCK: GET_QUOTA_ENDPOINT
