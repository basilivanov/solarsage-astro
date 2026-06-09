from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.db.models import HoraryCredit

from .test_horary_endpoints import _login


@pytest.mark.asyncio
async def test_list_questions_empty_on_200(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=301)

    r = await async_client.get("/api/horary/questions")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_questions_returns_401_without_session(
    async_client: AsyncClient,
) -> None:
    r = await async_client.get("/api/horary/questions")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_question_returns_404_for_nonexistent(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=302)

    r = await async_client.get(f"/api/horary/questions/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_question_returns_401_without_session(
    async_client: AsyncClient,
) -> None:
    r = await async_client.get(f"/api/horary/questions/{uuid.uuid4()}")
    assert r.status_code == 401
