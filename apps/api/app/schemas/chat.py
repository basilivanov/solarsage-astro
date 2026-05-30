# ############################################################################
# AI_HEADER: MODULE_CHAT_SCHEMA
# ROLE: Chat schemas for threads and messages
# DEPENDENCIES: pydantic
# GRACE_ANCHORS: [MESSAGE_CREATE, MESSAGE_RESPONSE, THREAD_RESPONSE]
# WAVE: W-CHAT-1
# ############################################################################

# START_MODULE_CONTRACT: M-CHAT-SCHEMA
# purpose: Pydantic schemas for chat API requests and responses
# owns:
#   - apps/api/app/schemas/chat.py
# inputs:
#   - none
# outputs:
#   - MessageCreate: request schema for creating a message
#   - MessageResponse: response schema for a message
#   - ThreadResponse: response schema for a thread with messages
# dependencies:
#   - pydantic
# side_effects:
#   - none
# invariants:
#   - role is "user" or "assistant"
# failure_policy:
#   - validation errors surface as 422 Unprocessable Entity
# non_goals:
#   - no business logic
# END_MODULE_CONTRACT: M-CHAT-SCHEMA

from pydantic import BaseModel


# START_BLOCK: MESSAGE_CREATE
class MessageCreate(BaseModel):
    """Create chat message."""
    content: str
# END_BLOCK: MESSAGE_CREATE


# START_BLOCK: MESSAGE_RESPONSE
class MessageResponse(BaseModel):
    """Chat message response."""
    id: str
    role: str
    content: str
    created_at: str
# END_BLOCK: MESSAGE_RESPONSE


# START_BLOCK: THREAD_RESPONSE
class ThreadResponse(BaseModel):
    """Chat thread response."""
    id: str
    title: str | None
    created_at: str
    updated_at: str
    messages: list[MessageResponse]
# END_BLOCK: THREAD_RESPONSE
