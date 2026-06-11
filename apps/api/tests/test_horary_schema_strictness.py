
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_HORARY_SCHEMA_STRICTNESS
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_horary_schema_strictness.py
# owns:
#   - apps/api/tests/test_horary_schema_strictness.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.horary import _normalize_horary_blocks, _to_question_read
from app.schemas.horary import HoraryAnswerRead, TimingBlock, VerdictCardBlock


def test_verdict_card_requires_confidence_fields() -> None:
    with pytest.raises(ValidationError):
        VerdictCardBlock.model_validate(
            {
                "type": "verdict_card",
                "verdict": "yes",
                "confidence": 0.8,
                "label": "Да",
            }
        )

    with pytest.raises(ValidationError):
        HoraryAnswerRead.model_validate(
            {
                "verdict": "yes",
                "confidence": 0.8,
                "blocks": [
                    {
                        "type": "verdict_card",
                        "verdict": "yes",
                        "confidence": 0.8,
                        "label": "Да",
                    }
                ],
                "planets": ["Sun"],
                "generatedAt": datetime.now(timezone.utc).isoformat(),
            }
        )


def test_timing_block_requires_status() -> None:
    with pytest.raises(ValidationError):
        TimingBlock.model_validate(
            {
                "type": "timing",
                "text": "Срок пока неясен, потому что карта не дает достаточно надежного временного указания.",
            }
        )


def test_old_answer_normalization() -> None:
    blocks = _normalize_horary_blocks(
        [
            {
                "type": "verdict_card",
                "verdict": "maybe",
                "confidence": 0.55,
                "label": "Скорее да",
            },
            {
                "type": "timing",
                "text": "Срок неясен, но развитие возможно после прояснения обстоятельств.",
            },
        ]
    )

    assert blocks[0]["confidenceLabel"] == "medium"
    assert blocks[0]["confidenceExplanation"] == ""
    assert blocks[1]["status"] == "unclear"

    class _Answer:
        verdict = "maybe"
        confidence = 0.55
        confidence_label = None
        confidence_explanation = None
        blocks_json = json.dumps(blocks, ensure_ascii=False)
        planets_json = json.dumps(["Moon"], ensure_ascii=False)
        generated_at = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)

    class _Question:
        id = "q-1"
        text = "Old answer"
        category = "other"
        status = "answered"
        spent_credit = None
        refund_status = "none"
        client_timezone = "UTC"
        client_local_time = None
        question_location_name = None
        failure_stage = None
        public_error_code = None
        public_error_message = None
        created_at = datetime(2026, 6, 9, 11, 0, tzinfo=timezone.utc)
        answer = _Answer()

    out = _to_question_read(_Question())
    assert out.answer is not None
    assert out.answer.confidence_label == "medium"
    assert out.answer.confidence_explanation == ""
    verdict_block = out.answer.blocks[0]
    timing_block = out.answer.blocks[1]
    assert isinstance(verdict_block, VerdictCardBlock)
    assert isinstance(timing_block, TimingBlock)
    assert verdict_block.confidence_label == "medium"
    assert verdict_block.confidence_explanation == ""
    assert timing_block.status == "unclear"
