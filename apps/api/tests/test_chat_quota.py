# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# ############################################################################
# AI_HEADER: MODULE_TEST_CHAT_QUOTA
# ROLE: Tests for chat quota functionality
# DEPENDENCIES: pytest, httpx, app.services.chat_quota_service
# GRACE_ANCHORS: [TEST_GET_QUOTA, TEST_QUOTA_ENFORCEMENT]
# WAVE: W-CHAT-4
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CHAT-QUOTA
# purpose: Test chat quota tracking and enforcement
# owns:
#   - apps/api/tests/test_chat_quota.py
# inputs:
#   - async_client: AsyncClient fixture
#   - make_initdata: fixture for creating Telegram initData
# outputs:
#   - test results (pass/fail)
# dependencies:
#   - M-CHAT-QUOTA-SERVICE
#   - M-API-CHAT (quota endpoint)
#   - M-PAYMENT-SERVICE (quota increase on subscription)
# side_effects:
#   - creates test users, threads, messages, quotas
# invariants:
#   - free tier: 10 messages
#   - subscription adds 100 messages
#   - quota enforced on user messages only
# failure_policy:
#   - tests fail if quota not enforced or not increased
# non_goals:
#   - no quota reset testing (requires time manipulation)
# END_MODULE_CONTRACT: M-TEST-CHAT-QUOTA

import pytest
from httpx import AsyncClient


# START_BLOCK: TEST_GET_QUOTA
@pytest.mark.asyncio
async def test_get_quota(async_client: AsyncClient, make_initdata):
    """Get chat quota. W-CHAT-4."""
    user_raw = make_initdata(user_id=12359, username="quotauser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.get("/api/chat/quota")

    assert response.status_code == 200
    data = response.json()
    assert data["messages_limit"] == 10  # Free tier
    assert data["messages_used"] == 0
    assert data["remaining"] == 10
    assert "reset_at" in data
# END_BLOCK: TEST_GET_QUOTA


# START_BLOCK: TEST_QUOTA_ENFORCEMENT
@pytest.mark.asyncio
async def test_quota_enforcement(async_client: AsyncClient, make_initdata):
    """Quota is enforced when sending messages. W-CHAT-4."""
    user_raw = make_initdata(user_id=12360, username="quotauser2")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Create thread
    thread_response = await async_client.post("/api/chat/threads")
    thread_id = thread_response.json()["id"]

    # Send 10 messages (free tier limit)
    for i in range(10):
        response = await async_client.post(
            f"/api/chat/threads/{thread_id}/messages",
            json={"content": f"Message {i}"}
        )
        assert response.status_code == 200

    # Check quota is exhausted
    quota_response = await async_client.get("/api/chat/quota")
    assert quota_response.json()["remaining"] == 0

    # 11th message should fail
    response = await async_client.post(
        f"/api/chat/threads/{thread_id}/messages",
        json={"content": "Message 11"}
    )
    assert response.status_code == 400  # Quota exceeded
    assert "quota" in response.json()["detail"].lower()
# END_BLOCK: TEST_QUOTA_ENFORCEMENT
