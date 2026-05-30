# ############################################################################
# AI_HEADER: MODULE_TEST_NATAL
# ROLE: Tests for natal reading endpoints.
# DEPENDENCIES: pytest, httpx, app.api.natal
# GRACE_ANCHORS: [TEST_NATAL_OVERVIEW, TEST_NATAL_SECTION]
# WAVE: W-7.2
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-NATAL
# purpose: Test natal reading endpoints (overview, section, not found).
# owns:
#   - apps/api/tests/test_natal.py
# inputs:
#   - async_client fixture
#   - make_initdata fixture
# outputs:
#   - test results
# dependencies:
#   - M-API-NATAL
#   - M-NATAL-SERVICE
# side_effects:
#   - creates test users
# invariants:
#   - tests require authentication
#   - tests verify response structure
# failure_policy:
#   - tests fail if endpoints return unexpected data
# non_goals:
#   - no integration with real LLM
# END_MODULE_CONTRACT: M-TEST-NATAL

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_natal_overview(async_client: AsyncClient, make_initdata):
    """
    Get natal reading overview.

    W-7.2: Verify overview returns meta + section list.
    """
    user_raw = make_initdata(user_id=12350, username="nataluser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.get("/api/natal/overview")

    assert response.status_code == 200
    data = response.json()
    assert "meta" in data
    assert "sections" in data

    # Verify meta structure
    meta = data["meta"]
    assert meta["schemaVersion"] == "natal/v1"
    assert meta["contractVersion"] == 1
    assert meta["title"] == "Натальная карта"
    assert "generatedAt" in meta

    # Verify sections list
    sections = data["sections"]
    assert len(sections) == 3  # sun, moon, ascendant
    assert sections[0]["id"] == "sun"
    assert sections[0]["title"] == "Солнце"
    assert sections[0]["iconName"] == "sun"
    assert sections[1]["id"] == "moon"
    assert sections[2]["id"] == "ascendant"


@pytest.mark.asyncio
async def test_get_natal_section(async_client: AsyncClient, make_initdata):
    """
    Get specific natal section.

    W-7.2: Verify section returns blocks.
    """
    user_raw = make_initdata(user_id=12351, username="nataluser2")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.get("/api/natal/section/sun")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "sun"
    assert data["title"] == "Солнце"
    assert data["iconName"] == "sun"
    assert "blocks" in data

    # Verify blocks structure
    blocks = data["blocks"]
    assert len(blocks) == 2  # paragraph + highlights

    # First block: paragraph
    assert blocks[0]["type"] == "paragraph"
    assert "text" in blocks[0]
    assert "Овна" in blocks[0]["text"]

    # Second block: highlights
    assert blocks[1]["type"] == "highlights"
    assert "items" in blocks[1]
    assert len(blocks[1]["items"]) == 2
    assert blocks[1]["items"][0]["title"] == "Сильные стороны"


@pytest.mark.asyncio
async def test_get_natal_section_moon(async_client: AsyncClient, make_initdata):
    """
    Get moon section with different block types.

    W-7.2: Verify moon section has paragraph, bullets, quote.
    """
    user_raw = make_initdata(user_id=12352, username="nataluser3")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.get("/api/natal/section/moon")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "moon"

    blocks = data["blocks"]
    assert len(blocks) == 3  # paragraph + bullets + quote

    # Verify block types
    assert blocks[0]["type"] == "paragraph"
    assert blocks[1]["type"] == "bullets"
    assert blocks[2]["type"] == "quote"

    # Verify bullets content
    assert len(blocks[1]["items"]) == 4
    assert "Сильная связь с семьей" in blocks[1]["items"][0]

    # Verify quote content
    assert "Луна в Раке" in blocks[2]["text"]
    assert blocks[2]["source"] == "Классическая астрология"


@pytest.mark.asyncio
async def test_get_natal_section_not_found(async_client: AsyncClient, make_initdata):
    """
    Get non-existent section returns 404.

    W-7.2: Verify 404 for invalid section_id.
    """
    user_raw = make_initdata(user_id=12353, username="nataluser4")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.get("/api/natal/section/invalid")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Section not found"


@pytest.mark.asyncio
async def test_get_natal_overview_unauthorized(async_client: AsyncClient):
    """
    Get natal overview without auth returns 401.

    W-7.2: Verify authentication is required.
    """
    response = await async_client.get("/api/natal/overview")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_natal_section_unauthorized(async_client: AsyncClient):
    """
    Get natal section without auth returns 401.

    W-7.2: Verify authentication is required.
    """
    response = await async_client.get("/api/natal/section/sun")

    assert response.status_code == 401
