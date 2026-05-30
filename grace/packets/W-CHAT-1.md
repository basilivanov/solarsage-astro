# W-CHAT-1 — Backend: chat contract, threads/messages storage, rate limit

## Decision

Create chat_threads and chat_messages tables. Each thread belongs to user, contains messages with role (user/assistant) and content. MVP version with echo bot (no real LLM integration yet).

## Acceptance Criteria

- [x] chat_threads table (id, user_id, title, timestamps)
- [x] chat_messages table (id, thread_id, role, content, created_at)
- [x] Migration 0008_add_chat_tables creates tables
- [x] ChatService.create_thread(), add_message(), get_messages()
- [x] POST /api/chat/threads — create thread
- [x] GET /api/chat/threads/{id} — get thread with messages
- [x] POST /api/chat/threads/{id}/messages — send message (echo bot MVP)
- [x] Tests: 5 tests passed (create thread, send message, get thread, not found, ownership)

## Evidence

- File: `/opt/solarsage-astro/apps/api/app/db/models.py` — ChatThread, ChatMessage models (lines 428-483)
- File: `/opt/solarsage-astro/apps/api/alembic/versions/0008_add_chat_tables.py` — Migration
- File: `/opt/solarsage-astro/apps/api/app/schemas/chat.py` — MessageCreate, MessageResponse, ThreadResponse schemas
- File: `/opt/solarsage-astro/apps/api/app/services/chat_service.py` — ChatService with create_thread, add_message, get_messages
- File: `/opt/solarsage-astro/apps/api/app/api/chat.py` — Three endpoints (create thread, get thread, send message)
- File: `/opt/solarsage-astro/apps/api/tests/test_chat.py` — 5 tests passed
- Migration applied: `alembic upgrade head` completed successfully

## Negative Tests

- [x] Get thread of another user → 404 (test_thread_ownership passed)
- [x] Get non-existent thread → 404 (test_get_thread_not_found passed)
- [ ] Send message to non-existent thread → error (covered by service layer ValueError)
- [ ] Rate limit: >10 messages/minute → 429 (deferred to W-RATELIMIT)

## Notes

- MVP version: assistant responds with echo "Вы сказали: {content}"
- Real LLM integration deferred to future wave
- Rate limiting deferred to W-RATELIMIT
- Thread ownership verified at service layer
