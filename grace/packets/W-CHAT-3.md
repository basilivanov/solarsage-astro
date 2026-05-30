# W-CHAT-3 — Observability: flip chat.* events from reserved to emitted

## Decision

Emit chat.thread_created and chat.message_sent events via structured logging (logger.info with extra fields). Events include user_id, thread_id, message_id, role, and event_type.

## Acceptance Criteria

- [x] chat.thread_created event on thread creation
- [x] chat.message_sent event on message send
- [x] Events include thread_id, message_id, role, user_id
- [x] Events emitted via app.core.logging.logger (structured logging)

## Evidence

- File: `/opt/solarsage-astro/apps/api/app/services/chat_service.py` — Event emission in create_thread() and add_message()
  - Lines 59-67: chat.thread_created event
  - Lines 107-116: chat.message_sent event
- Pattern: `logger.info("event_type", extra={...})` with event_type, user_id, thread_id, message_id, role

## Negative Tests

- [x] Event emission failure doesn't block chat operation (logger.info is fire-and-forget, no await)

## Notes

- Uses existing structured logging infrastructure (W-1.6, W-1.7)
- Events go to stdout via backend logger
- No database persistence for events (observability only)
- Event format compatible with centralized log aggregation
