# ############################################################################
# AI_HEADER: MODULE_CHAT_SERVICE
# ROLE: Chat service for threads and messages
# DEPENDENCIES: sqlalchemy, app.db.models, app.services.log_service
# GRACE_ANCHORS: [CREATE_THREAD, GET_THREAD, ADD_MESSAGE, GET_MESSAGES]
# WAVE: W-CHAT-1, W-CHAT-3
# ############################################################################

# START_MODULE_CONTRACT: M-CHAT-SERVICE
# purpose: Business logic for chat threads and messages
# owns:
#   - apps/api/app/services/chat_service.py
# inputs:
#   - db: AsyncSession
#   - user_id: UUID
#   - thread_id: UUID
#   - role: str ("user", "assistant")
#   - content: str
# outputs:
#   - ChatThread: created or retrieved thread
#   - ChatMessage: created message
#   - list[ChatMessage]: messages in thread
# dependencies:
#   - M-DB-MODELS (ChatThread, ChatMessage)
#   - M-LOG-SERVICE (W-CHAT-3: event emission)
# side_effects:
#   - creates rows in chat_threads, chat_messages
#   - emits chat.thread_created, chat.message_sent events (W-CHAT-3)
# invariants:
#   - thread ownership verified before operations
#   - thread.updated_at updated on new message
# failure_policy:
#   - ValueError if thread not found or not owned by user
# non_goals:
#   - no LLM integration (MVP echo bot)
# END_MODULE_CONTRACT: M-CHAT-SERVICE

# START_MODULE_MAP: M-CHAT-SERVICE
# public_entrypoints:
#   - create_thread
#   - get_thread
#   - add_message
#   - get_messages
# semantic_blocks:
#   - CREATE_THREAD: create new chat thread
#   - GET_THREAD: get thread with messages
#   - ADD_MESSAGE: add message to thread
#   - GET_MESSAGES: get all messages in thread
# END_MODULE_MAP: M-CHAT-SERVICE

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.models import ChatMessage, ChatThread
from app.core.logging import log_event, log_block
from app.services.chat_quota_service import ChatQuotaService


class ChatService:
    """Chat service. W-CHAT-1, W-CHAT-3."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # START_BLOCK: CREATE_THREAD
    async def create_thread(self, user_id: uuid.UUID) -> ChatThread:
        # START_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.create_thread
        # purpose: Create new chat thread for user.
        # inputs: user_id (UUID)
        # returns: ChatThread with id, created_at
        # side_effects: creates ChatThread row, emits chat.thread_created event
        # emitted_logs: chat.thread_created
        # error_behavior: DB errors propagate
        # END_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.create_thread
        """Create new chat thread."""
        thread = ChatThread(user_id=user_id)
        self.db.add(thread)
        await self.db.commit()
        await self.db.refresh(thread)

        # W-CHAT-3: Emit event
        with log_block(slice="W-CHAT", module="M-CHAT-SERVICE", block="CREATE_THREAD"):
            log_event(
                "chat.thread_created",
                payload={
                    "thread_id": str(thread.id),
                },
            )

        return thread
    # END_BLOCK: CREATE_THREAD

    # START_BLOCK: GET_THREAD
    async def get_thread(
        self,
        thread_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ChatThread | None:
        # START_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.get_thread
        # purpose: Get chat thread by id, verifying user ownership.
        # inputs: thread_id (UUID), user_id (UUID)
        # returns: ChatThread or None if not found/not owned
        # side_effects: reads from DB
        # emitted_logs: none
        # error_behavior: returns None on not found; never raises
        # END_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.get_thread
        """Get thread with messages."""
        result = await self.db.execute(
            select(ChatThread)
            .where(
                ChatThread.id == thread_id,
                ChatThread.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
    # END_BLOCK: GET_THREAD

    # START_BLOCK: ADD_MESSAGE
    async def add_message(
        self,
        thread_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        content: str,
    ) -> ChatMessage:
        # START_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.add_message
        # purpose: Add message to thread with quota check and ownership verification.
        # inputs: thread_id (UUID), user_id (UUID), role (str), content (str)
        # returns: ChatMessage with id, role, content, created_at
        # side_effects: creates ChatMessage row, updates ChatThread.updated_at, checks/uses quota
        # emitted_logs: chat.message_sent
        # error_behavior: raises ValueError if thread not found, quota exceeded
        # END_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.add_message
        """Add message to thread."""
        # W-CHAT-4: Check quota for user messages
        if role == "user":
            quota_service = ChatQuotaService(self.db)
            has_quota = await quota_service.check_quota(user_id)

            if not has_quota:
                raise ValueError("Chat quota exceeded")

            # Increment usage
            await quota_service.increment_usage(user_id)

        # Verify thread ownership
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            raise ValueError("Thread not found")

        message = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
        )
        self.db.add(message)

        # Update thread updated_at
        thread.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(message)

        # W-CHAT-3: Emit event
        with log_block(slice="W-CHAT", module="M-CHAT-SERVICE", block="ADD_MESSAGE"):
            log_event(
                "chat.message_sent",
                payload={
                    "thread_id": str(thread_id),
                    "message_id": str(message.id),
                    "role": role,
                },
            )

        return message
    # END_BLOCK: ADD_MESSAGE

    # START_BLOCK: GET_MESSAGES
    async def get_messages(
        self,
        thread_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ChatMessage]:
        # START_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.get_messages
        # purpose: Get all messages in thread ordered by creation time.
        # inputs: thread_id (UUID), user_id (UUID)
        # returns: list[ChatMessage] sorted by created_at
        # side_effects: reads from DB
        # emitted_logs: none
        # error_behavior: returns empty list if thread not found
        # END_FUNCTION_CONTRACT: F-M-CHAT-SERVICE.get_messages
        """Get all messages in thread."""
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            return []

        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())
    # END_BLOCK: GET_MESSAGES
