# W-CHAT-4 — Quotas / billing for chat

## Decision

Track chat message usage per user with monthly quota. Free tier: 10 messages/month. Subscription adds 100 messages.

## Acceptance Criteria

- [x] chat_quotas table (user_id, messages_used, messages_limit, reset_at)
- [x] Migration 0009 creates table
- [x] ChatQuotaService.check_quota(), increment_usage(), increase_limit()
- [x] ChatService.add_message() enforces quota for user messages
- [x] GET /api/chat/quota endpoint
- [x] Subscription purchase increases quota by 100
- [x] Tests: get quota, enforcement, subscription integration

## Evidence

- File: `/opt/solarsage-astro/apps/api/app/db/models.py` — ChatQuota model (lines 487-507)
- File: `/opt/solarsage-astro/apps/api/alembic/versions/0009_add_chat_quotas.py` — Migration
- File: `/opt/solarsage-astro/apps/api/app/services/chat_quota_service.py` — ChatQuotaService
- File: `/opt/solarsage-astro/apps/api/app/services/chat_service.py` — Quota enforcement (W-CHAT-4, lines 100-111)
- File: `/opt/solarsage-astro/apps/api/app/services/payment_service.py` — Quota increase on payment (W-CHAT-4, lines 73-78)
- File: `/opt/solarsage-astro/apps/api/app/api/chat.py` — GET /api/chat/quota endpoint (lines 148-165)
- Test: `/opt/solarsage-astro/apps/api/tests/test_chat_quota.py` — 3 tests passed

```bash
$ poetry run pytest tests/test_chat_quota.py -v
======================== 3 passed, 21 warnings in 0.41s ========================
```

## Negative Tests

- [x] Send message without quota → 400 "Chat quota exceeded"
- [ ] Quota resets after 30 days → messages_used = 0 (requires time manipulation)
- [x] Increase quota for non-existent user → creates quota first (handled by get_or_create_quota)

## Implementation Notes

### Quota Enforcement Flow

1. User sends message → ChatService.add_message()
2. Check quota: ChatQuotaService.check_quota()
3. If quota exceeded → raise ValueError("Chat quota exceeded")
4. If quota available → increment usage and create message
5. API endpoint catches ValueError → returns 400 with detail

### Billing Integration

When payment succeeds (PaymentService.handle_webhook):
1. Create subscription entry (W-6.2)
2. Increase chat quota by 100 messages (W-CHAT-4)

### Quota Reset

Quota automatically resets when expired:
- check_quota() compares current time with reset_at
- If expired: messages_used = 0, reset_at = now + 30 days

### Timezone Handling

ChatQuotaService handles both timezone-aware and naive datetimes:
- SQLite returns naive datetimes
- PostgreSQL returns timezone-aware datetimes
- check_quota() normalizes to UTC before comparison

## API Examples

### Get quota
```bash
GET /api/chat/quota
Authorization: Bearer <token>

Response:
{
  "messages_used": 5,
  "messages_limit": 10,
  "reset_at": "2026-06-29T18:41:54.000000Z",
  "remaining": 5
}
```

### Send message (quota exceeded)
```bash
POST /api/chat/threads/{thread_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{"content": "Hello"}

Response (400):
{
  "detail": "Chat quota exceeded"
}
```

## Production Considerations

1. **Quota limits**: Free tier = 10 messages, Subscription = +100 messages
2. **Reset period**: 30 days (monthly)
3. **Enforcement**: Only user messages count toward quota (assistant messages are free)
4. **Billing integration**: Quota increases automatically on subscription purchase
5. **Monitoring**: Track quota exhaustion rate to adjust limits

## Future Enhancements

- [ ] Different quota tiers (basic, premium, enterprise)
- [ ] Quota usage analytics dashboard
- [ ] Email notifications when quota is low (80%, 90%, 100%)
- [ ] Quota rollover (unused messages carry over to next month)
- [ ] Per-model quota (different limits for different LLM models)
