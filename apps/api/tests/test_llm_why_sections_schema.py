# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_LLM_WHY_SECTIONS_SCHEMA — why boundary proofs.
# ROLE: Proves the fail-closed JSON schema boundary of generate_why_sections:
#       valid JSON with wrong TYPES (the release E2E 29894386844 form:
#       sections[i].text as a JSON array) is rejected with None + canonical
#       llm.response_rejected (reason=schema_invalid only) — never an
#       exception and never a 500; valid payloads behave unchanged.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-LLM-WHY-SECTIONS-SCHEMA
# purpose: Directed tests for the why-sections JSON type boundary.
# owns:
#   - apps/api/tests/test_llm_why_sections_schema.py
# inputs: mocked LLMService._generate_text at the parser boundary.
# outputs: None-vs-sections assertions and sanitized rejection-log shape.
# dependencies: LLMService and pytest fixtures only.
# side_effects: none (transport mocked; production parse code runs for real).
# emitted_logs: none.
# invariants:
#   - Any explicitly provided wrong type or blank text rejects the batch.
#   - Absent trailing sections / absent text field keep the ctx fallback.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-LLM-WHY-SECTIONS-SCHEMA

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm_service import LLMService

CONTEXTS = [
    {"layer": "main_theme", "title": "Тема", "context": "контекст темы", "blocks_kind": "paragraph"},
    {"layer": "day_factors", "title": "Факторы", "context": "контекст факторов", "blocks_kind": "paragraph"},
    {"layer": "actions", "title": "Действия", "context": "- действие одно\n- действие два", "blocks_kind": "bullets"},
]


async def _run_why(raw_response: str, contexts=None):
    service = LLMService()
    with patch.object(LLMService, "_generate_text", new_callable=AsyncMock) as mock_gen, \
         patch("app.services.llm_service.log_event") as mock_log:
        mock_gen.return_value = raw_response
        result = await service.generate_why_sections(contexts or CONTEXTS)
    return result, mock_log


def _assert_rejected(result, mock_log) -> None:
    assert result is None
    mock_log.assert_called_once()
    args, kwargs = mock_log.call_args
    assert args[0] == "llm.response_rejected"
    assert kwargs["payload"] == {"reason": "schema_invalid"}


# -- rejection shapes ---------------------------------------------------------

@pytest.mark.asyncio
async def test_top_level_list_rejected():
    result, mock_log = await _run_why('[{"sections": []}]')
    _assert_rejected(result, mock_log)


@pytest.mark.asyncio
async def test_sections_mapping_not_list_rejected():
    result, mock_log = await _run_why('{"sections": {"why-1": {"text": "x"}}}')
    _assert_rejected(result, mock_log)


@pytest.mark.asyncio
async def test_section_item_not_dict_rejected():
    result, mock_log = await _run_why('{"sections": ["why-1", {"id": "why-2", "text": "ok"}]}')
    _assert_rejected(result, mock_log)


@pytest.mark.asyncio
async def test_text_as_json_array_rejected_ci_form():
    # Exact release E2E 29894386844 form: valid JSON, sections[i].text is a
    # JSON array — old code raised AttributeError on text.split -> /api/day 500.
    raw = '{"sections": [{"id": "why-1", "text": ["строка один", "строка два"]}]}'
    result, mock_log = await _run_why(raw, contexts=CONTEXTS[:1])
    _assert_rejected(result, mock_log)


@pytest.mark.asyncio
async def test_blank_text_rejected():
    for blank in ['""', '"   "']:
        raw = '{"sections": [{"id": "why-1", "text": %s}]}' % blank
        result, mock_log = await _run_why(raw, contexts=CONTEXTS[:1])
        _assert_rejected(result, mock_log)


@pytest.mark.asyncio
async def test_null_text_rejected():
    result, mock_log = await _run_why('{"sections": [{"id": "why-1", "text": null}]}', contexts=CONTEXTS[:1])
    _assert_rejected(result, mock_log)


@pytest.mark.asyncio
async def test_rejection_log_has_no_raw_response():
    secret_text = "уникальный текст ответа модели"
    raw = '{"sections": [{"id": "why-1", "text": ["%s"]}]}' % secret_text
    result, mock_log = await _run_why(raw, contexts=CONTEXTS[:1])
    assert result is None
    _, kwargs = mock_log.call_args
    assert secret_text not in str(kwargs)


# -- unchanged valid behavior -------------------------------------------------

@pytest.mark.asyncio
async def test_valid_payload_unchanged():
    raw = (
        '{"sections": ['
        '{"id": "why-1", "text": "Первый текст."},'
        '{"id": "why-2", "text": "Второй текст."},'
        '{"id": "why-3", "text": "- раз\\n- два\\n- три"}'
        "]}"
    )
    result, mock_log = await _run_why(raw)
    assert result is not None
    mock_log.assert_not_called()
    assert [s["id"] for s in result] == ["why-1", "why-2", "why-3"]
    assert result[0]["blocks"] == [{"kind": "paragraph", "text": "Первый текст."}]
    assert result[2]["blocks"] == [{"kind": "bullets", "items": ["раз", "два", "три"]}]


@pytest.mark.asyncio
async def test_missing_trailing_section_uses_ctx_fallback():
    raw = '{"sections": [{"id": "why-1", "text": "Только первая."}]}'
    result, mock_log = await _run_why(raw)
    assert result is not None
    mock_log.assert_not_called()
    assert result[0]["blocks"][0]["text"] == "Только первая."
    # Missing trailing sections keep the deterministic ctx context.
    assert result[1]["blocks"][0]["text"] == "контекст факторов"
    assert result[2]["blocks"][0]["items"] == ["действие одно", "действие два"]


@pytest.mark.asyncio
async def test_missing_text_field_uses_ctx_fallback():
    raw = '{"sections": [{"id": "why-1"}, {"id": "why-2", "text": "Есть текст."}, {"id": "why-3"}]}'
    result, mock_log = await _run_why(raw)
    assert result is not None
    mock_log.assert_not_called()
    assert result[0]["blocks"][0]["text"] == "контекст темы"
    assert result[1]["blocks"][0]["text"] == "Есть текст."
