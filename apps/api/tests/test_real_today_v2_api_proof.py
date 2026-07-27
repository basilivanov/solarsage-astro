# ############################################################################
# AI_HEADER: TEST_REAL_TODAY_V2_API_PROOF — unit tests, no I/O.
# ROLE: Test proof utility's typed outcomes, validation, redaction, CLI, main.
# ############################################################################
# START_MODULE_CONTRACT: M-TEST-REAL-TODAY-V2-API-PROOF
# purpose: Pure unit tests. Uses committed fixture + mock I/O. No network/DB.
# owns: apps/api/tests/test_real_today_v2_api_proof.py
# dependencies: scripts.prove_today_v2_real_api
# side_effects: none. emitted_logs: none.
# END_MODULE_CONTRACT: M-TEST-REAL-TODAY-V2-API-PROOF
# START_MODULE_MAP: M-TEST-REAL-TODAY-V2-API-PROOF
# public_entrypoints: 6 test_* functions. owned_tests: self.
# END_MODULE_MAP: M-TEST-REAL-TODAY-V2-API-PROOF

import ast
import asyncio
import json
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient, MockTransport

# Repo root on sys.path so `import scripts.*` works regardless of pytest cwd
# (CI runs from repo root, local runs from apps/api per AGENTS.md).
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.prove_today_v2_real_api import (
    CANON_PROFILE,
    PipelineUnavailable,
    ProofErrorCode,
    ProofFailure,
    _raw_version_code,
    build_redacted_proof,
    check_sidecar_health,
    main,
    parse_args,
    parse_sidecar_health,
    request_proof,
    validate_today_v2_payload,
)

FX = REPO_ROOT / "e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json"


@pytest.fixture(scope="module")
def fx():
    # START_FUNCTION_CONTRACT: F-TEST.fx
    # purpose: Load canonical fixture.
    # inputs: none.
    # returns: dict.
    # side_effects: reads file.
    # emitted_logs: none.
    # error_behavior: skips.
    # END_FUNCTION_CONTRACT: F-TEST.fx
    if not FX.exists():
        pytest.skip("fixture missing")
    with open(FX) as f:
        return json.load(f)


@pytest.fixture
def v(fx):
    d = deepcopy(fx)
    if "v2" in d and d["v2"] and "audit" in d["v2"] and "canonVersions" in d["v2"]["audit"]:
        from app.services.canon_service import get_canon_versions
        d["v2"]["audit"]["canonVersions"] = get_canon_versions()
    return d


def _val(raw):
    return validate_today_v2_payload(raw)

# ── 1. Validation cases ────────────────────────────────────────────
@pytest.mark.parametrize("field,val,code", [
    ("calculationVersion","x","calculation_version_mismatch"),
    ("activationLayerVersion","x","activation_version_mismatch"),
    ("scoringVersion","x","scoring_version_mismatch"),
    ("payloadVersion","today.v1","payload_version_mismatch"),
    ("frontendPayloadVersion",2,"frontend_version_mismatch"),
    ("contentVersion",9,"content_version_mismatch"),
])
def test_validation_cases(v, field, val, code):
    # START_FUNCTION_CONTRACT: F-TEST.test_validation_cases
    # purpose: Prove exact version error codes.
    # inputs: v, field, val, code.
    # returns: None.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises.
    # END_FUNCTION_CONTRACT: F-TEST.test_validation_cases
    v["meta"][field] = val
    with pytest.raises(ProofFailure) as e:
        _val(v)
    assert e.value.code.value == code

def test_six_field_fallback(v):
    # START_FUNCTION_CONTRACT: F-TEST.test_six_field_fallback
    # purpose: Prove ValidationError fallback checks all 6 fields.
    # inputs: v.
    # returns: None.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises.
    # END_FUNCTION_CONTRACT: F-TEST.test_six_field_fallback
    # Both payload and calculation wrong: exact version code wins
    cp = deepcopy(v)
    cp["meta"]["calculationVersion"] = "wrong"
    cp["meta"]["frontendPayloadVersion"] = 2  # also wrong
    with pytest.raises(ProofFailure) as e:
        _val(cp)
    assert e.value.code.value == "calculation_version_mismatch"

# ── 2. Redaction cases ─────────────────────────────────────────────
def test_redaction_cases(v):
    # START_FUNCTION_CONTRACT: F-TEST.test_redaction_cases
    # purpose: Prove redacted output shape, IDs, forbidden content, hash.
    # inputs: v.
    # returns: None.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-TEST.test_redaction_cases
    p = _val(v)
    r = build_redacted_proof(p, "asgi", "2026-07-08")
    assert r["status"]=="pass"
    assert [h["id"] for h in r["horizons"]]==["long","medium","fast"]
    assert r["versions"]["payload"]=="today.v2.1"
    from app.services.canon_service import get_canon_versions
    assert len(r["canonKeys"]) == len(get_canon_versions())
    s = json.dumps(r)
    def _scan(obj, path=""):
        if isinstance(obj,dict):
            for k,val in obj.items():
                p2=f"{path}.{k}"
                for pat in ["birthday","birthLat","headline","firstName","initData"]:
                    if pat in k.casefold():
                        assert False, f"forbidden key: {p2}"
                    if isinstance(val,str) and pat in val.casefold():
                        assert False, f"forbidden value: {p2}"
                _scan(val,p2)
        elif isinstance(obj,list):
            for i,val in enumerate(obj):
                _scan(val,f"{path}[{i}]")
    _scan(r)
    all_ids = set()
    for item in v["v2"]["horizons"]["items"]:
        all_ids.update(item.get("activationIds",[]))
    for ev in v["v2"].get("activationEvidence",[]):
        all_ids.add(ev["id"])
    for rid in all_ids:
        assert rid not in s, f"raw ID leaked: {rid}"
    p2=_val(v)
    ids=list(p2.v2.horizons.items[0].activation_ids)
    ids.reverse()
    p2.v2.horizons.items[0].activation_ids=ids
    assert r["horizons"][0]["activationIdsSha256"]==build_redacted_proof(p2,"asgi","2026-07-08")["horizons"][0]["activationIdsSha256"]
    # Exact CANON_PROFILE shape matching document 82
    assert CANON_PROFILE=={"firstName":"Dev","gender":"female","birth":{"birthday":"1990-01-01","birthTime":"12:00:00","birthCity":"Moscow, Russia","birthLat":55.7558,"birthLon":37.6173,"birthTz":"Europe/Moscow"},"currentLocation":{"city":"Moscow, Russia","lat":55.7558,"lon":37.6173,"tz":"Europe/Moscow"}}

# ── 3. Request phase cases (real MockTransport behavior) ───────────
@pytest.mark.parametrize("scenario,cookie_val,day_status,day_body,expected_code", [
    ("auth_fail",None,401,None,"auth_failed"),
    ("no_cookie","",200,None,"secure_cookie_missing"),
    ("profile_fail","session=v",401,None,"profile_failed"),
    ("day_fail","session=v",200,None,"day_failed"),
    ("day_bad_json","session=v",200,"not-json","day_failed"),
])
def test_request_phase_cases(scenario, cookie_val, day_status, day_body, expected_code):
    # START_FUNCTION_CONTRACT: F-TEST.test_request_phase_cases
    # purpose: Prove 5 HTTP phases map to exact owned closed codes.
    # inputs: scenario, cookie_val, day_status, day_body, expected_code.
    # returns: None.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test assertions.
    # END_FUNCTION_CONTRACT: F-TEST.test_request_phase_cases
    import httpx
    def _handler(req):
        if req.url.path=="/api/auth/dev":
            if "auth_fail" in scenario:
                return httpx.Response(401, request=req)
            hdrs = {} if not cookie_val else {"set-cookie":f"grace_session_v2={cookie_val};path=/;httponly;secure;samesite=none"}
            return httpx.Response(200, headers=hdrs, request=req, json={})
        if req.url.path=="/api/profile":
            if "profile_fail" in scenario:
                return httpx.Response(401, request=req)
            return httpx.Response(200, request=req, json={})
        if req.url.path.startswith("/api/day/"):
            if "day_fail" in scenario:
                return httpx.Response(day_status or 500, request=req)
            if "day_bad" in scenario:
                return httpx.Response(200, request=req, text="not-json")
            return httpx.Response(200, request=req, json={})
        return httpx.Response(404, request=req)
    transport = MockTransport(_handler)
    async def _run():
        async with AsyncClient(transport=transport, base_url="https://127.0.0.1") as c:
            try:
                await request_proof(c, "asgi", "2026-07-08")
                return None
            except ProofFailure as e:
                return e.code.value
            except Exception:
                return "unexpected_error"
    code = asyncio.run(_run())
    assert code == expected_code, f"{scenario}: expected {expected_code}, got {code}"

# ── 4. CLI and output cases ────────────────────────────────────────
def test_cli_and_output_cases(tmp_path, capsys):
    # START_FUNCTION_CONTRACT: F-TEST.test_cli_and_output_cases
    # purpose: Prove CLI validation, emit_outcome, main matrix via capsys.
    # inputs: tmp_path, capsys.
    # returns: None.
    # side_effects: monkeypatched I/O.
    # emitted_logs: none.
    # error_behavior: test assertions.
    # END_FUNCTION_CONTRACT: F-TEST.test_cli_and_output_cases
    a=parse_args([])
    assert a.date=="2026-07-08" and a.transport=="asgi"
    with pytest.raises(ProofFailure,match="invalid_date"):
        parse_args(["--date","x"])
    with pytest.raises(ProofFailure,match="invalid_base_url"):
        parse_args(["--base-url","http://[::1"])
    with pytest.raises(ProofFailure,match="invalid_base_url"):
        parse_args(["--base-url","http://localhost:bad"])
    with pytest.raises(ProofFailure,match="invalid_cli"):
        parse_args(["--transport","x"])
    out_file = tmp_path / "proof.json"
    ma=MagicMock()
    ma.out=str(out_file)
    ma.date="2026-07-08"
    ma.transport="asgi"
    ma.base_url=""
    for outcome,expected_code,status_key in [("pass",0,"pass"),("unavailable",1,"unavailable"),
      ("error",1,"error"),("internal",1,"error")]:
        with patch("scripts.prove_today_v2_real_api.parse_args",return_value=ma), \
             patch("scripts.prove_today_v2_real_api.check_sidecar_health"), \
             patch("scripts.prove_today_v2_real_api.run_asgi_proof") as m, \
             patch("scripts.prove_today_v2_real_api.Path.write_text"):
            if outcome=="unavailable":
                m.side_effect=PipelineUnavailable("missing_long")
            elif outcome=="error":
                m.side_effect=ProofFailure(ProofErrorCode.activation_version_mismatch)
            elif outcome=="internal":
                m.side_effect=RuntimeError("boom")
            else:
                m.return_value={"status":"pass","date":"x","versions":{}}
            ec = main()
            captured=capsys.readouterr()
            lines=[line for line in captured.out.strip().split("\n") if line]
            assert len(lines)==1, f"{outcome}: expected 1 line, got {len(lines)}"
            assert not captured.err, f"{outcome}: stderr not empty"
            obj=json.loads(lines[0])
            assert obj["status"]==status_key
            assert ec==expected_code
            if outcome=="error":
                assert obj["code"]=="activation_version_mismatch"
            if outcome=="internal":
                assert obj["code"]=="internal_error"
    # Write OSError
    with patch("scripts.prove_today_v2_real_api.parse_args",return_value=ma), \
         patch("scripts.prove_today_v2_real_api.check_sidecar_health"), \
         patch("scripts.prove_today_v2_real_api.run_asgi_proof") as m, \
         patch("scripts.prove_today_v2_real_api.Path.write_text",side_effect=OSError("denied")):
        m.return_value={"status":"pass","date":"x","versions":{}}
        ec = main()
        captured=capsys.readouterr()
        obj=json.loads(captured.out.strip())
        assert obj["code"]=="invalid_out_path"
        assert not captured.err
        assert ec==1
    # Sidecar health fail stops transport
    with patch("scripts.prove_today_v2_real_api.parse_args",return_value=ma), \
         patch("scripts.prove_today_v2_real_api.check_sidecar_health",
               side_effect=ProofFailure(ProofErrorCode.sidecar_unhealthy)), \
         patch("scripts.prove_today_v2_real_api.run_asgi_proof") as m:
        ec = main()
        captured=capsys.readouterr()
        assert m.call_count==0
        assert ec==1
        obj=json.loads(captured.out.strip())
        assert obj["code"]=="sidecar_unhealthy"
        assert not captured.err

# ── 5. Source contract cases ───────────────────────────────────────
def test_source_contract_cases():
    # START_FUNCTION_CONTRACT: F-TEST.test_source_contract_cases
    # purpose: Prove AST, cookie/text guards, Make recipe.
    # inputs: none.
    # returns: None.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-TEST.test_source_contract_cases
    src=(REPO_ROOT / "scripts/prove_today_v2_real_api.py").read_text()
    tree=ast.parse(src)
    calls={}
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef):
            calls[node.name]=sum(1 for n in ast.walk(node)
                if isinstance(n,ast.Call) and getattr(n.func,'id',None)=='request_proof')
    assert calls.get("run_asgi_proof",0)==1
    assert calls.get("run_http_proof",0)==1
    for pat in ['"set-cookie',"'set-cookie'",".cookies.get(",".cookies[",'Cookie:']:
        assert pat not in src
    for pat in ["str(exc)","repr(exc)","traceback","pipeline status","DBG:"]:
        assert pat not in src
    mk=(REPO_ROOT / "Makefile").read_text()
    assert "unexport DATE" in mk and "unexport PROOF_DATE" in mk
    assert "$(value DATE)" in mk and "$(value OUT)" in mk
    assert "$(value TRANSPORT)" in mk and "$(value BASE_URL)" in mk
    assert "$${PROOF_RUN_DATE}" in mk and "$${PROOF_RUN_OUT}" in mk
    assert "$${PROOF_RUN_TRANSPORT}" in mk and "$${PROOF_RUN_BASE_URL}" in mk

# ── 6. Health and _raw_version_code cases ──────────────────────────
def test_health_and_version_cases(v):
    # START_FUNCTION_CONTRACT: F-TEST.test_health_and_version_cases
    # purpose: Prove sidecar health, _raw_version_code, canon regressions.
    # inputs: v.
    # returns: None.
    # side_effects: monkeypatched httpx.
    # emitted_logs: none.
    # error_behavior: test assertions.
    # END_FUNCTION_CONTRACT: F-TEST.test_health_and_version_cases
    assert parse_sidecar_health(200,{"ok":True}) is True
    assert parse_sidecar_health(500,{"ok":True}) is False
    with patch("httpx.get") as m:
        m.return_value.status_code=500
        m.return_value.json.return_value={"ok":False}
        with pytest.raises(ProofFailure,match="sidecar_unhealthy"):
            check_sidecar_health()
    assert _raw_version_code({"meta":{"calculationVersion":"wrong"}}) is not None
    assert _raw_version_code({"meta":{"payloadVersion":"today.v2.1"}}) is None
    v2=deepcopy(v["v2"])
    v3=deepcopy(v["v2"])
    v2["audit"]["canonVersions"].pop("horizon_selection",None)
    with pytest.raises(ProofFailure,match="canon_keys_mismatch"):
        validate_today_v2_payload({**v,"v2":v2})
    v3["audit"]["canonVersions"]["extra"]="v1"
    with pytest.raises(ProofFailure,match="canon_keys_mismatch"):
        validate_today_v2_payload({**v,"v2":v3})
    v["v2"]=None
    with pytest.raises(ProofFailure,match="payload_validation_failed"):
        _val(v)
