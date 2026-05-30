# ############################################################################
# AI_HEADER: MODULE_TEST_CHAT
# ROLE: Tests for chat endpoints
# DEPENDENCIES: pytest, httpx, app.api.chat
# GRACE_ANCHORS: [TEST_CREATE_THREAD, TEST_SEND_MESSAGE, TEST_GET_THREAD]
# WAVE: W-CHAT-1, W-CHAT-3
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CHAT
# purpose: Integration tests for chat API endpoints
# owns:
#   - apps/api/tests/test_chat.py
# inputs:
#   - async_client: AsyncClient fixture
#   - make_initdata: fixture for creating Telegram initData
# outputs:
#   - test results
# dependencies:
#   - M-API-CHAT
#   - M-CHAT-SERVICE
# side_effects:
#   - creates test users, threads, messages
# invariants:
#   - each test uses unique user
# failure_policy:
#   - test failures surface as pytest failures
# non_goals:
#   - no unit tests (integration only)
# END_MODULE_CONTRACT: M-TEST-CHAT

import pytest
from httpx import AsyncClient


# START_BLOCK: TEST_CREATE_THREAD
@pytest.mark.asyncio
async def test_create_thread(async_client: AsyncClient, make_initdata):
    """Create chat thread. W-CHAT-1."""
    user_raw = make_initdata(user_id=12356, username="chatuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.post("/api/chat/threads")

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "created_at" in data
# END_BLOCK: TEST_CREATE_THREAD


# START_BLOCK: TEST_SEND_MESSAGE
@pytest.mark.asyncio
async def test_send_message(async_client: AsyncClient, make_initdata):
    """Send message to thread. W-CHAT-1."""
    user_raw = make_initdata(user_id=12357, username="chatuser2")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Create thread
    thread_response = await async_client.post("/api/chat/threads")
    thread_id = thread_response.json()["id"]

    # Send message
    response = await async_client.post(
        f"/api/chat/threads/{thread_id}/messages",
        json={"content": "Привет!"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_message"]["content"] == "Привет!"
    assert data["assistant_message"]["role"] == "assistant"
    assert "Вы сказали:" in data["assistant_message"]["content"]
# END_BLOCK: TEST_SEND_MESSAGE


# START_BLOCK: TEST_GET_THREAD
@pytest.mark.asyncio
async def test_get_thread(async_client: AsyncClient, make_initdata):
    """Get thread with messages. W-CHAT-1."""
    user_raw = make_initdata(user_id=12358, username="chatuser3")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Create thread + send message
    thread_response = await async_client.post("/api/chat/threads")
    thread_id = thread_response.json()["id"]

    await async_client.post(
        f"/api/chat/threads/{thread_id}/messages",
        json={"content": "Тест"}
    )

    # Get thread
    response = await async_client.get(f"/api/chat/threads/{thread_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2  # user + assistant
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
# END_BLOCK: TEST_GET_THREAD


# START_BLOCK: TEST_THREAD_NOT_FOUND
@pytest.mark.asyncio
async def test_get_thread_not_found(async_client: AsyncClient, make_initdata):
    """Get non-existent thread returns 404. W-CHAT-1."""
    user_raw = make_initdata(user_id=12359, username="chatuser4")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Try to get non-existent thread
    response = await async_client.get("/api/chat/threads/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
# END_BLOCK: TEST_THREAD_NOT_FOUND


# START_BLOCK: TEST_THREAD_OWNERSHIP
@pytest.mark.asyncio
async def test_thread_ownership(async_client: AsyncClient, make_initdata):
    """Cannot access another user's thread. W-CHAT-1."""
    # User 1 creates thread
    user1_raw = make_initdata(user_id=12360, username="chatuser5")
    await async_client.post("/api/auth/telegram", json={"initData": user1_raw})
    thread_response = await async_client.post("/api/chat/threads")
    thread_id = thread_response.json()["id"]

    # User 2 tries to access it
    user2_raw = make_initdata(user_id=12361, username="chatuser6")
    await async_client.post("/api/auth/telegram", json={"initData": user2_raw})
    response = await async_client.get(f"/api/chat/threads/{thread_id}")

    assert response.status_code == 404
# END_BLOCK: TEST_THREAD_OWNERSHIP
