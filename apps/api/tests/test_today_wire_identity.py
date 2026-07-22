# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TODAY_WIRE_IDENTITY — V2 wire identity contract.
# ROLE: Proves the V2 discriminator contract: meta.payload_version (today.v2/
#       today.v2.1) + coherent frontend_payload_version + v2 block drive
#       identity; meta.schema_version stays Literal "today/v1" for ALL
#       series; the wire dump is camelCase while the debug/oracle dump stays
#       snake_case and byte-stable.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-TODAY-WIRE-IDENTITY
# purpose: Directed contract tests for the today.v2.x wire identity model.
# owns:
#   - apps/api/tests/test_today_wire_identity.py
# inputs: built payload fixtures (test_today_horizons_contract builder).
# outputs: assertions on validation, aliases, and dump stability.
# dependencies: TodayPayload, build_complete_today_payload.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - schema_version "today/v1" is accepted for every series.
#   - Incoherent current payload/frontend pair is rejected.
#   - V2 identity without a v2 block is rejected.
#   - by_alias=False debug dump is snake_case and byte-stable.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-TODAY-WIRE-IDENTITY

from __future__ import annotations

import json

import pytest

from app.schemas.today import TodayPayload
from tests.test_today_horizons_contract import build_complete_today_payload


def test_v2_1_wire_root_validates_and_serializes_camel() -> None:
    model = TodayPayload.model_validate(
        build_complete_today_payload(
            payload_version="today.v2.1",
            frontend_payload_version=3,
            audit_payload_version="today.v2.1",
            include_pipeline_audit=True,
        )
    )
    # schema_version "today/v1" is the canonical literal for ALL series.
    assert model.meta.schema_version == "today/v1"
    assert model.meta.payload_version == "today.v2.1"
    assert model.meta.frontend_payload_version == 3

    wire = model.model_dump(mode="json", by_alias=True)
    wire_meta = wire["meta"]
    assert wire_meta["payloadVersion"] == "today.v2.1"
    assert wire_meta["frontendPayloadVersion"] == 3
    assert wire_meta["schemaVersion"] == "today/v1"
    assert "generatedAt" in wire_meta
    assert "generated_at" not in wire_meta

    # The debug/oracle dump stays the internal snake_case form.
    debug = model.model_dump(mode="json", by_alias=False)
    debug_meta = debug["meta"]
    assert debug_meta["payload_version"] == "today.v2.1"
    assert debug_meta["frontend_payload_version"] == 3
    assert "generated_at" in debug_meta
    assert "generatedAt" not in debug_meta


def test_incoherent_current_pair_rejected() -> None:
    with pytest.raises(ValueError, match="exact payload/frontend version pair"):
        TodayPayload.model_validate(
            build_complete_today_payload(
                payload_version="today.v2.1",
                frontend_payload_version=2,
                audit_payload_version="today.v2.1",
                include_pipeline_audit=True,
            )
        )


def test_v2_identity_without_v2_block_rejected() -> None:
    payload = build_complete_today_payload(
        payload_version="today.v2",
        frontend_payload_version=2,
        audit_payload_version="today.v2",
        include_pipeline_audit=False,
    )
    payload["v2"] = None
    with pytest.raises(ValueError, match="requires v2 block"):
        TodayPayload.model_validate(payload)


def test_frozen_debug_dump_byte_stable() -> None:
    """The frozen baseline contour derives the internal debug dump from the
    production model: two validations of the same input are byte-identical."""
    raw = build_complete_today_payload(
        payload_version="today.v2.1",
        frontend_payload_version=3,
        audit_payload_version="today.v2.1",
        include_pipeline_audit=True,
    )
    dump1 = TodayPayload.model_validate(raw).model_dump(mode="json", by_alias=False)
    dump2 = TodayPayload.model_validate(raw).model_dump(mode="json", by_alias=False)
    assert json.dumps(dump1, sort_keys=True) == json.dumps(dump2, sort_keys=True)
