# ############################################################################
# AI_HEADER: MODULE_API_TODAY_FIXTURE_CONTRACT_TEST
# ROLE: Python integration tests for visual JSON fixture contract validation.
# DEPENDENCIES: pytest, json, sys, pathlib, app.schemas.today.TodayPayload
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-FIXTURE-CONTRACT
# purpose: Verify that e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json is fully valid against backend TodayPayload.
# owns:
#   - apps/api/tests/test_today_fixture_contract.py
# inputs: e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
# outputs: pytest assertion results
# dependencies: apps/api/app/schemas/today.py
# side_effects: none
# emitted_logs: none
# invariants:
#   - visual JSON fixture validates under strict TodayPayload
#   - normalized round-trip matches identical IDs and verdicts
# failure_policy: fail test
# END_MODULE_CONTRACT: M-TEST-TODAY-FIXTURE-CONTRACT

# START_MODULE_MAP: M-TEST-TODAY-FIXTURE-CONTRACT
# public_entrypoints: test functions
# semantic_blocks:
#   - FIXTURE_ROUNDTRIP_TESTS: validates Pydantic model validation, dump formatting, timing types, and advice verdicts.
# owned_tests:
#   - apps/api/tests/test_today_fixture_contract.py
# END_MODULE_MAP: M-TEST-TODAY-FIXTURE-CONTRACT

# START_BLOCK: FIXTURE_ROUNDTRIP_TESTS
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.contracts.normalize_today_fixture import normalize_file  # noqa: E402
from app.schemas.today import TodayPayload  # noqa: E402

FIXTURE_PATH = REPO_ROOT / "e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json"


def test_fixture_pydantic_validation():
    """1. canonical JSON passes strict TodayPayload.model_validate"""
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_fixture_pydantic_validation
    # purpose: Validate the canonical fixture against the strict Today payload model.
    # inputs: none.
    # returns: none.
    # side_effects: reads the committed fixture.
    # emitted_logs: none.
    # error_behavior: assertions expose fixture or schema drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_fixture_pydantic_validation
    assert FIXTURE_PATH.is_file()
    raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    model = TodayPayload.model_validate(data)
    assert model.date == "2026-07-08"
    assert model.v2 is not None


def test_fixture_normalization_roundtrip():
    """2-5. normalized model_dump matches details, timing, and advice verdicts"""
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_fixture_normalization_roundtrip
    # purpose: Prove strict model roundtrip preserves activation timing and advice verdicts.
    # inputs: none.
    # returns: none.
    # side_effects: reads the committed fixture.
    # emitted_logs: none.
    # error_behavior: assertions expose normalization drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_fixture_normalization_roundtrip
    raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    model = TodayPayload.model_validate(data)

    dumped = model.model_dump(mode="json", by_alias=True, exclude_unset=True)

    # 2. contains camelCase timing
    evidence_dumped = dumped["v2"]["activationEvidence"]
    assert any("activeFrom" in ev for ev in evidence_dumped)

    # 3. raw -> normalized activation ID order and set are equal
    orig_ev_ids = [ev["id"] for ev in data["v2"]["activationEvidence"]]
    dumped_ev_ids = [ev["id"] for ev in dumped["v2"]["activationEvidence"]]
    assert orig_ev_ids == dumped_ev_ids

    # 4. timing map id -> (activeFrom, exactAt, activeUntil) is equal
    orig_timing = {
        ev["id"]: (
            ev.get("activeFrom"),
            ev.get("exactAt"),
            ev.get("activeUntil"),
        )
        for ev in data["v2"]["activationEvidence"]
    }
    dumped_timing = {
        ev["id"]: (
            ev.get("activeFrom"),
            ev.get("exactAt"),
            ev.get("activeUntil"),
        )
        for ev in dumped["v2"]["activationEvidence"]
    }
    assert orig_timing == dumped_timing

    # 5. verdict map row.key -> row.verdict is equal
    orig_verdicts = {
        row["key"]: row["verdict"]
        for row in data["concreteAdvice"]["rows"]
    }
    dumped_verdicts = {
        row["key"]: row["verdict"]
        for row in dumped["concreteAdvice"]["rows"]
    }
    assert orig_verdicts == dumped_verdicts


def test_normalizer_check_and_idempotence(tmp_path):
    """6-8. check mode, normalization and idempotence of normalize_today_fixture"""
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_normalizer_check_and_idempotence
    # purpose: Prove normalizer check behavior, writes, missing-path handling, and idempotence.
    # inputs: tmp_path - pytest-managed isolated directory.
    # returns: none.
    # side_effects: reads the committed fixture and writes temporary fixture copies.
    # emitted_logs: none.
    # error_behavior: assertions expose normalizer contract drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_normalizer_check_and_idempotence
    # 6. normalizer --check returns clean (0) on canonical fixture
    res = normalize_file(FIXTURE_PATH, check_only=True)
    assert res == 0

    # 7. drifted copy in temp dir gives check failure (1), bytes unchanged
    temp_fixture = tmp_path / "drifted.json"
    raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
    # inject trailing space inside raw text or modify key order
    drifted_text = raw_text.replace('"date": "2026-07-08",', '"date":  "2026-07-08",')
    temp_fixture.write_text(drifted_text, encoding="utf-8")

    res_drift = normalize_file(temp_fixture, check_only=True)
    assert res_drift == 1
    # Check that file content did not change in check mode
    assert temp_fixture.read_text(encoding="utf-8") == drifted_text

    # 8. normalize temp copy twice gives byte-identical result
    res_norm1 = normalize_file(temp_fixture, check_only=False)
    assert res_norm1 == 0
    sha_1 = Path(temp_fixture).read_text(encoding="utf-8")

    res_norm2 = normalize_file(temp_fixture, check_only=False)
    assert res_norm2 == 0
    sha_2 = Path(temp_fixture).read_text(encoding="utf-8")
    assert sha_1 == sha_2

    # test: missing_parent / fixture.json + check_only=True -> non-zero, parent not created
    missing_parent_dir = tmp_path / "non_existing_parent_dir"
    missing_parent_fixture = missing_parent_dir / "fixture.json"
    res_missing = normalize_file(missing_parent_fixture, check_only=True)
    assert res_missing == 2
    assert not missing_parent_dir.exists()

    # test: missing_parent / fixture.json + check_only=False -> non-zero, parent not created
    res_missing_write = normalize_file(missing_parent_fixture, check_only=False)
    assert res_missing_write == 2
    assert not missing_parent_dir.exists()


def test_invalid_fixture_sanitized_error(tmp_path, capsys):
    """9. invalid fixture error does not print test sentinel or raw input"""
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_invalid_fixture_sanitized_error
    # purpose: Prove invalid-fixture diagnostics redact sentinel and raw payload content.
    # inputs: tmp_path - isolated directory; capsys - captured process output.
    # returns: none.
    # side_effects: writes a temporary invalid fixture and captures normalizer output.
    # emitted_logs: none.
    # error_behavior: assertions expose status-code or privacy regressions.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-FIXTURE-CONTRACT.test_invalid_fixture_sanitized_error
    sentinel = "TEST_SENTINEL_SECRET"
    bad_data = {
        "date": "2026-07-08",
        "headline": sentinel,
        "dayStatus": "invalid_status",  # causes ValidationError
    }
    temp_bad = tmp_path / "bad.json"
    temp_bad.write_text(json.dumps(bad_data), encoding="utf-8")

    res = normalize_file(temp_bad, check_only=False)
    assert res == 5

    captured = capsys.readouterr()
    # Check that sentinel is not leaked in stdout or stderr
    assert sentinel not in captured.out
    assert sentinel not in captured.err
    assert "dayStatus" in captured.err

    # check that full raw payload is not logged
    bad_data_serialized = json.dumps(bad_data)
    assert bad_data_serialized not in captured.out
    assert bad_data_serialized not in captured.err
# END_BLOCK: FIXTURE_ROUNDTRIP_TESTS
