# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NATAL_SECTION_RETRY — per-section retry proofs.
# ROLE: Proves the natal section generation contract: strict provider JSON
#       schema on every section call, exactly one bounded retry for the
#       CURRENT failed section (successful sections never regenerated), and
#       FAILED_RETRYABLE after two rejected attempts — never a partial/READY.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-NATAL-SECTION-RETRY
# purpose: Directed tests for the natal section retry + structured-output
#   boundary (release run 29916959921 class: one rejected section killing
#   the whole report).
# owns:
#   - apps/api/tests/test_natal_section_retry.py
# inputs: mocked LLMService._generate_text and NatalContextService.
# outputs: call-count, json_schema and status assertions.
# dependencies: sqlite in-memory DB; app services.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Only the failed section is retried (exactly one extra call).
#   - Two rejected attempts keep FAILED_RETRYABLE without partial sections.
#   - Every section call carries the strict natal json_schema.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-NATAL-SECTION-RETRY

from __future__ import annotations

import json
import uuid
from datetime import date as Date, time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import NatalChartCache, User, UserProfile
from app.db.session import Base
from app.schemas.natal import NatalChartAngle, NatalChartHouse, NatalChartPlanet, NatalContextData
from app.services.natal_report_service import _NATAL_SECTION_JSON_SCHEMA, NatalReportService

def _provider_block(block_type: str, **fields) -> dict:
    """Provider-shaped flattened block: every schema key present, null for
    inapplicable fields (strict json_schema requires all flattened keys)."""
    block = {
        "type": block_type,
        "text": None,
        "level": None,
        "items": None,
        "ordered": None,
        "title": None,
        "tone": None,
        "prosLabel": None,
        "consLabel": None,
        "pros": None,
        "cons": None,
        "source": None,
    }
    block.update(fields)
    return block


VALID_SECTION_JSON = json.dumps(
    {
        "blocks": [
            _provider_block("paragraph", text="Конкретный текст раздела о характере человека."),
            # Flattened nulls on optional properties must parse cleanly.
            _provider_block("heading", text="Подзаголовок раздела", level=None),
            _provider_block("callout", title="Совет", text="Практический совет.", tone=None),
        ]
    },
    ensure_ascii=False,
)


async def _run_generation(llm_side_effect):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user_id = uuid.uuid4()
        session.add(User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18)))
        await session.commit()
        session.add(UserProfile(
            user_id=user_id, first_name="Test", gender="female",
            birthday=Date(1993, 1, 7), birth_time=time(10, 33),
            birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
            birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
            is_onboarded=True,
        ))
        profile_hash = "testhash123"
        session.add(NatalChartCache(
            user_id=user_id, profile_hash=profile_hash,
            raw_chart_json="{}", normalized_context_json="{}",
        ))
        await session.commit()

        service = NatalReportService(session)
        mock_context = NatalContextData(
            planets=[
                NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9, retrograde=False),
                NatalChartPlanet(name="Moon", sign="Gemini", degree=29.6, house=4, longitude=119.6, retrograde=False),
            ],
            houses=[
                NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30))
                for i in range(1, 13)
            ],
            aspects=[],
            angles=[NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9)],
        )

        with patch("app.services.natal_report_service.NatalContextService") as MockCtxSvc, \
             patch("app.services.llm_service.LLMService") as MockLLM:
            mock_ctx_instance = AsyncMock()
            mock_ctx_instance.get_or_build_natal_context.return_value = mock_context
            MockCtxSvc.return_value = mock_ctx_instance
            MockCtxSvc.compute_profile_hash = MagicMock(return_value=profile_hash)

            mock_llm = AsyncMock()
            mock_llm._generate_text.side_effect = llm_side_effect
            MockLLM.return_value = mock_llm

            result = await service.generate_report(user_id)
    await engine.dispose()
    return result, mock_llm


@pytest.mark.asyncio
async def test_failed_section_retried_once_then_succeeds() -> None:
    # 8 sections: first two succeed, the THIRD fails once then succeeds,
    # the rest succeed — exactly ONE extra call total (no regeneration of
    # the already-successful sections).
    responses = (
        [VALID_SECTION_JSON, VALID_SECTION_JSON]
        + ["not json at all", VALID_SECTION_JSON]
        + [VALID_SECTION_JSON] * 5
    )
    result, mock_llm = await _run_generation(responses)

    assert result.status == "READY", f"expected READY after one bounded retry, got {result.status}"
    assert result.sections_available
    assert mock_llm._generate_text.call_count == 9  # 8 sections + 1 retry of the failed one


@pytest.mark.asyncio
async def test_two_rejected_attempts_produce_failed_retryable_without_partial() -> None:
    # The FIRST section rejects twice -> immediate FAILED_RETRYABLE; no
    # further sections are attempted, nothing partial or READY persists.
    result, mock_llm = await _run_generation(["not json at all", "still not json"])

    assert result.status == "FAILED_RETRYABLE"
    assert not result.sections_available
    assert mock_llm._generate_text.call_count == 2  # exactly two attempts of the failed section


@pytest.mark.asyncio
async def test_every_section_call_carries_strict_json_schema() -> None:
    result, mock_llm = await _run_generation([VALID_SECTION_JSON] * 8)

    assert result.status == "READY"
    assert mock_llm._generate_text.call_count == 8
    for call in mock_llm._generate_text.call_args_list:
        schema = call.kwargs.get("json_schema")
        assert schema is not None, "natal section call missing strict json_schema"
        assert schema is _NATAL_SECTION_JSON_SCHEMA
        assert schema["strict"] is True
        assert schema["schema"]["additionalProperties"] is False
        assert schema["schema"]["required"] == ["blocks"]
        block_types = schema["schema"]["properties"]["blocks"]["items"]["properties"]["type"]["enum"]
        assert set(block_types) == {
            "lead", "paragraph", "heading", "list", "callout", "pros_cons", "quote", "divider",
        }


@pytest.mark.asyncio
async def test_structural_reject_then_provider_shaped_valid_succeeds() -> None:
    # First attempt: syntactically VALID JSON with a wrong root (top-level
    # list) — previously an AttributeError that bypassed the retry; now a
    # normalized structural rejection. Second attempt: valid provider-shaped
    # response with flattened null keys -> READY after exactly one retry.
    responses = (
        [VALID_SECTION_JSON, VALID_SECTION_JSON]
        + ["[]", VALID_SECTION_JSON]
        + [VALID_SECTION_JSON] * 5
    )
    result, mock_llm = await _run_generation(responses)

    assert result.status == "READY", f"expected READY after structural retry, got {result.status}"
    assert mock_llm._generate_text.call_count == 9


@pytest.mark.asyncio
async def test_two_structural_rejects_produce_failed_retryable() -> None:
    # Root wrong on attempt 1, blocks:null on attempt 2 — both are
    # normalized structural rejections: FAILED_RETRYABLE with exactly 2
    # calls, no partial sections.
    result, mock_llm = await _run_generation(["[]", '{"blocks": null}'])

    assert result.status == "FAILED_RETRYABLE"
    assert not result.sections_available
    assert mock_llm._generate_text.call_count == 2


# -- Schema↔parser gap proofs (provider-valid but previously Pydantic-invalid) -

def _block(block_type: str, **fields) -> dict:
    block = {
        "type": block_type,
        "text": None,
        "level": 2,
        "items": [],
        "ordered": False,
        "title": None,
        "tone": None,
        "prosLabel": None,
        "consLabel": None,
        "pros": [],
        "cons": [],
        "source": None,
    }
    block.update(fields)
    return block


def test_out_of_enum_tone_normalized_to_info() -> None:
    # tone is a presentation-only display hint. The strict provider schema
    # now ENUMS tone, so "tip" is never provider-valid — this normalization
    # is the parser defense for legacy/non-enforcing responses (DeepSeek
    # fallback without a schema) and the exact pre-fix failure class.
    from app.services.natal_report_service import NatalReportService

    blocks = NatalReportService._parse_blocks([
        _block("callout", title="Совет", text="Действуй спокойно.", tone="tip")
    ])
    assert len(blocks) == 1
    assert blocks[0].tone == "info"


def test_null_items_fail_closed() -> None:
    # Explicit null list content is a structural rejection (bounded retry
    # fires for the section) — never normalized into an empty block.
    from app.services.natal_report_service import NatalReportService

    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("list", items=None)])


def test_empty_list_and_blank_items_fail_closed() -> None:
    from app.services.natal_report_service import NatalReportService

    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("list", items=[])])
    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("list", items=["", "   "])])


def test_empty_pros_cons_fail_closed_but_one_side_ok() -> None:
    from app.services.natal_report_service import NatalReportService

    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("pros_cons", pros=[], cons=[])])
    blocks = NatalReportService._parse_blocks([
        _block("pros_cons", pros=[{"title": "Сила", "text": "Опора на сильные стороны."}], cons=[])
    ])
    assert len(blocks) == 1


def test_pros_cons_null_or_malformed_side_rejected() -> None:
    from app.services.natal_report_service import NatalReportService

    valid_item = {"title": "Сила", "text": "Опора на сильные стороны."}
    # Explicit null side (even with a valid other side) -> reject.
    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("pros_cons", pros=None, cons=[valid_item])])
    # Non-list side -> reject.
    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("pros_cons", pros="bad", cons=[valid_item])])
    # Non-dict item -> reject.
    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("pros_cons", pros=["bad"], cons=[valid_item])])


def test_pros_cons_blank_item_rejected() -> None:
    from app.services.natal_report_service import NatalReportService

    valid_item = {"title": "Сила", "text": "Опора на сильные стороны."}
    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("pros_cons", pros=[{"title": "", "text": "x"}], cons=[valid_item])])
    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("pros_cons", pros=[{"title": "Сила", "text": "  "}], cons=[valid_item])])


def test_null_narrative_text_stays_fail_closed() -> None:
    # Narrative text is real content: null must never be normalized into a
    # fake report.
    from app.services.natal_report_service import NatalReportService

    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("paragraph", text=None)])


def test_unknown_block_type_still_rejected() -> None:
    from app.services.natal_report_service import NatalReportService

    with pytest.raises(ValueError):
        NatalReportService._parse_blocks([_block("table", text="x")])


def test_strict_schema_enums_and_non_null_arrays() -> None:
    from app.services.natal_report_service import _NATAL_SECTION_JSON_SCHEMA

    props = _NATAL_SECTION_JSON_SCHEMA["schema"]["properties"]["blocks"]["items"]["properties"]
    assert props["tone"]["enum"] == ["info", "warning", "insight", "positive", None]
    assert props["tone"]["type"] == ["string", "null"]
    assert props["items"]["type"] == "array"
    assert props["items"]["items"] == {"type": "string"}
    assert props["ordered"]["type"] == "boolean"
    assert props["level"]["type"] == "integer"
    assert props["pros"]["type"] == "array"
    assert props["cons"]["type"] == "array"


@pytest.mark.asyncio
async def test_provider_shaped_optional_values_parse_without_retry() -> None:
    # The exact PRE-FIX failure class from deploy run 29939799948: a
    # legacy-or-non-enforcing response shape (e.g. DeepSeek fallback) with a
    # presentation-only out-of-enum tone. The strict provider schema now
    # PREVENTS that tone at the boundary; the parser defense here proves a
    # non-enforcing shape still succeeds on the FIRST attempt (no retry
    # consumed) and produces a READY report.
    creative = json.dumps(
        {
            "blocks": [
                _block("lead", text="Раздел открывается сильной темой личности."),
                _block("paragraph", text="Текст раздела о характере человека."),
                _block("callout", title="Совет", text="Действуй спокойно и не торопи события.", tone="tip"),
                _block("list", items=["Практичный шаг один", "Практичный шаг два"]),
            ]
        },
        ensure_ascii=False,
    )
    result, mock_llm = await _run_generation([creative] * 8)

    assert result.status == "READY", f"expected READY, got {result.status}"
    assert mock_llm._generate_text.call_count == 8  # zero retries consumed


@pytest.mark.asyncio
async def test_null_list_full_generation_failed_retryable() -> None:
    # A null list anywhere in a section is a structural rejection: the
    # bounded retry fires exactly once per section, and two identical
    # rejections keep the FAILED_RETRYABLE contract — never READY.
    bad = json.dumps(
        {
            "blocks": [
                _block("lead", text="Раздел открывается сильной темой личности."),
                _block("list", items=None),
            ]
        },
        ensure_ascii=False,
    )
    result, mock_llm = await _run_generation([bad, bad])

    assert result.status == "FAILED_RETRYABLE"
    assert not result.sections_available
    assert mock_llm._generate_text.call_count == 2
