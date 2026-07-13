#!/usr/bin/env python3
# AI_HEADER: SCRIPT_PROVE_TODAY_V2_REAL_API — fail-closed proof.
# START_MODULE_CONTRACT: M-PROVE-TODAY-V2-REAL-API
# purpose: E2E proof; typed outcomes; no leaks. side_effects: modifies dev user.
# END_MODULE_CONTRACT: M-PROVE-TODAY-V2-REAL-API
# START_MODULE_MAP: M-PROVE-TODAY-V2-REAL-API
# entrypoints: validate, build, request, run_* checks, main
# END_MODULE_MAP: M-PROVE-TODAY-V2-REAL-API
import argparse, enum, hashlib, json, os
from datetime import date as Date; from pathlib import Path
from urllib.parse import urlsplit
CANON_PROFILE = {"firstName":"Dev","gender":"female","birth":{"birthday":"1990-01-01","birthTime":"12:00:00","birthCity":"Moscow, Russia","birthLat":55.7558,"birthLon":37.6173,"birthTz":"Europe/Moscow"},"currentLocation":{"city":"Moscow, Russia","lat":55.7558,"lon":37.6173,"tz":"Europe/Moscow"}}
class ProofErrorCode(str, enum.Enum):
    invalid_cli="invalid_cli";invalid_date="invalid_date";invalid_transport="invalid_transport"
    invalid_out_path="invalid_out_path";invalid_base_url="invalid_base_url"
    sidecar_unhealthy="sidecar_unhealthy";auth_failed="auth_failed"
    secure_cookie_missing="secure_cookie_missing";secure_cookie_requires_https="secure_cookie_requires_https"
    profile_failed="profile_failed";day_failed="day_failed"
    payload_validation_failed="payload_validation_failed"
    calculation_version_mismatch="calculation_version_mismatch"
    activation_version_mismatch="activation_version_mismatch"
    scoring_version_mismatch="scoring_version_mismatch";payload_version_mismatch="payload_version_mismatch";frontend_version_mismatch="frontend_version_mismatch";content_version_mismatch="content_version_mismatch"
    audit_alignment_failed="audit_alignment_failed";canon_keys_mismatch="canon_keys_mismatch"
    horizon_validation_failed="horizon_validation_failed";internal_error="internal_error"
class ProofFailure(Exception):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.ProofFailure
    # purpose: Typed error. inputs: code. side_effects: none. emitted_logs: none.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.ProofFailure
    def __init__(self, code: ProofErrorCode): self.code = code
class PipelineUnavailable(Exception):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.PipelineUnavailable
    # purpose: Typed unavailable. inputs: reason. side_effects: none. emitted_logs: none.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.PipelineUnavailable
    def __init__(self, reason: str): self.reason = reason
def _sha256_sorted(ids): return hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()
def _raw_version_code(raw: dict) -> ProofErrorCode | None:
    from app.core.versions import (ACTIVATION_LAYER_VERSION, CALCULATION_VERSION,
        SCORING_V2_VERSION, TODAY_V2_PAYLOAD_VERSION, V2_FRONTEND_PAYLOAD_VERSION,
        TODAY_CONTENT_VERSION)
    m = raw.get("meta", {})
    for field, const, code in [("calculationVersion",CALCULATION_VERSION,"calculation_version_mismatch"),
      ("activationLayerVersion",ACTIVATION_LAYER_VERSION,"activation_version_mismatch"),
      ("scoringVersion",SCORING_V2_VERSION,"scoring_version_mismatch"),
      ("contentVersion",TODAY_CONTENT_VERSION,"content_version_mismatch"),
      ("payloadVersion",TODAY_V2_PAYLOAD_VERSION,"payload_version_mismatch"),
      ("frontendPayloadVersion",V2_FRONTEND_PAYLOAD_VERSION,"frontend_version_mismatch")]:
        val = m.get(field)
        if val is not None and val != const: return ProofErrorCode(code)
    return None
def parse_sidecar_health(status_code: int, body: dict) -> bool:
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.parse_sidecar_health
    # purpose: Parse sidecar health.
    # inputs: status_code, body.
    # returns: True if 200 and ok.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: returns False.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.parse_sidecar_health
    return status_code == 200 and body.get("ok") is True
def check_sidecar_health():
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.check_sidecar_health
    # purpose: Sidecar preflight before auth.
    # inputs: none.
    # returns: None.
    # side_effects: HTTP GET to 18091.
    # emitted_logs: none.
    # error_behavior: raises ProofFailure(sidecar_unhealthy).
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.check_sidecar_health
    import httpx
    try:
        r = httpx.get("http://127.0.0.1:18091/v1/health", timeout=5)
        if not parse_sidecar_health(r.status_code, r.json()):
            raise ProofFailure(ProofErrorCode.sidecar_unhealthy)
    except ProofFailure: raise
    except Exception: raise ProofFailure(ProofErrorCode.sidecar_unhealthy)
def validate_today_v2_payload(raw: dict):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.validate_today_v2_payload
    # purpose: Validate raw JSON through TodayPayload.
    # inputs: raw dict.
    # returns: TodayPayload.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises PipelineUnavailable or ProofFailure.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.validate_today_v2_payload
    from app.schemas.today import TodayPayload
    from app.core.versions import (ACTIVATION_LAYER_VERSION, CALCULATION_VERSION,
        SCORING_V2_VERSION, TODAY_V2_PAYLOAD_VERSION, V2_FRONTEND_PAYLOAD_VERSION,
        TODAY_CONTENT_VERSION)
    from app.services.canon_service import get_canon_versions
    import pydantic
    try: p = TodayPayload.model_validate(raw)
    except pydantic.ValidationError:
        code = _raw_version_code(raw)
        if code: raise ProofFailure(code)
        raise ProofFailure(ProofErrorCode.payload_validation_failed)
    m = p.meta
    for val,exp,code in [(m.calculation_version,CALCULATION_VERSION,"calculation"),(m.activation_layer_version,ACTIVATION_LAYER_VERSION,"activation"),(m.scoring_version,SCORING_V2_VERSION,"scoring"),(m.content_version,TODAY_CONTENT_VERSION,"content")]:
        if val!=exp: raise ProofFailure(ProofErrorCode(code+"_version_mismatch"))
    if p.v2 is None: raise ProofFailure(ProofErrorCode.payload_validation_failed)
    v2, audit = p.v2, p.v2.audit
    if audit.horizon_pipeline is None: raise ProofFailure(ProofErrorCode.payload_validation_failed)
    hp = audit.horizon_pipeline
    if hp.status == "unavailable": raise PipelineUnavailable(hp.reason)
    if hp.status != "built" or hp.reason != "selected" or hp.selected_count != 3:
        raise ProofFailure(ProofErrorCode.audit_alignment_failed)
    if audit.payload_version != m.payload_version: raise ProofFailure(ProofErrorCode.audit_alignment_failed)
    if set(audit.canon_versions.keys()) != set(get_canon_versions().keys()):
        raise ProofFailure(ProofErrorCode.canon_keys_mismatch)
    if v2.horizons is None: raise ProofFailure(ProofErrorCode.payload_validation_failed)
    hz = v2.horizons
    if hz.schema_version != "today-horizons.v1": raise ProofFailure(ProofErrorCode.horizon_validation_failed)
    if hz.guidance_mode != "deterministic": raise ProofFailure(ProofErrorCode.horizon_validation_failed)
    types_seen = []
    for item in hz.items:
        t = item.timing; types_seen.append(item.horizon)
        if not t.active_from or not t.active_until or not t.state or not t.timezone:
            raise ProofFailure(ProofErrorCode.horizon_validation_failed)
        if not item.activation_ids: raise ProofFailure(ProofErrorCode.horizon_validation_failed)
        if item.horizon in ("medium","fast") and (not t.exact_at or not t.peak_label):
            raise ProofFailure(ProofErrorCode.horizon_validation_failed)
        if not item.manifestations or not item.actions.do or not item.actions.avoid:
            raise ProofFailure(ProofErrorCode.horizon_validation_failed)
    if types_seen != ["long","medium","fast"]: raise ProofFailure(ProofErrorCode.horizon_validation_failed)
    ev_ids = {ev.id for ev in v2.activation_evidence}
    all_ids = {a for i in hz.items for a in i.activation_ids}
    if all_ids - ev_ids: raise ProofFailure(ProofErrorCode.horizon_validation_failed)
    return p
def build_redacted_proof(payload, transport, date_val):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.build_redacted_proof
    # purpose: Build redacted proof artifact from typed TodayPayload.
    # inputs: payload — typed TodayPayload; transport — "asgi"|"http";
    #   date_val — ISO date string.
    # returns: allowlist dict with no profile/copy/raw IDs.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.build_redacted_proof
    m, v2, audit = payload.meta, payload.v2, payload.v2.audit
    hz, hp = v2.horizons, audit.horizon_pipeline
    horizons = []
    for item in hz.items:
        act_ids = list(item.activation_ids)
        horizons.append({"id":item.horizon,"tone":item.tone,"timingState":item.timing.state,
            "hasRange":bool(item.timing.active_from and item.timing.active_until),
            "hasPeak":bool(item.timing.exact_at),"activationCount":len(act_ids),
            "activationIdsSha256":_sha256_sorted(act_ids) if act_ids else "",
            "manifestationCount":len(item.manifestations),"doCount":len(item.actions.do),
            "avoidCount":len(item.actions.avoid),"likelySpheres":list(item.likely_spheres)})
    return {"schemaVersion":"today-v2-real-api-proof.v1","status":"pass","transport":transport,
        "date":date_val,"authPath":"/api/auth/dev","dayPath":f"/api/day/{date_val}",
        "sidecarHealth":"pass","versions":{"calculation":m.calculation_version,
            "activation":m.activation_layer_version,"scoring":m.scoring_version,
            "payload":m.payload_version,"frontend":m.frontend_payload_version,
            "content":m.content_version},"pipeline":{"status":hp.status,
            "selectedCount":hp.selected_count,"guidanceMode":hz.guidance_mode},
        "horizons":horizons,"activationEvidenceCount":len(v2.activation_evidence),
        "canonKeys":sorted(audit.canon_versions.keys()),"fixtureDependency":False}
async def request_proof(client, transport, date_val):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.request_proof
    # purpose: Shared auth/profile/day boundary.
    # inputs: client, transport, date_val.
    # returns: redacted proof dict.
    # side_effects: HTTP calls; modifies dev profile.
    # emitted_logs: none.
    # error_behavior: raises ProofFailure per phase.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.request_proof
    from app.core.config import settings
    import httpx
    try: r = await client.post("/api/auth/dev"); r.raise_for_status()
    except Exception: raise ProofFailure(ProofErrorCode.auth_failed) from None
    try:
        if settings.session_cookie_name not in client.cookies:
            raise ProofFailure(ProofErrorCode.secure_cookie_missing)
    except ProofFailure: raise
    except Exception: raise ProofFailure(ProofErrorCode.auth_failed) from None
    try: r = await client.put("/api/profile", json=CANON_PROFILE); r.raise_for_status()
    except Exception: raise ProofFailure(ProofErrorCode.profile_failed) from None
    try:
        r = await client.get(f"/api/day/{date_val}"); r.raise_for_status()
        raw = r.json()
    except httpx.HTTPError: raise ProofFailure(ProofErrorCode.day_failed) from None
    except json.JSONDecodeError: raise ProofFailure(ProofErrorCode.day_failed) from None
    return build_redacted_proof(validate_today_v2_payload(raw), transport, date_val)
def _silence_stdio():
    import sys; sys.stdout.flush(); sys.stderr.flush()
    dn = os.open(os.devnull, os.O_WRONLY); os.dup2(dn, 1); os.dup2(dn, 2)
    sys.stdout = os.fdopen(os.dup(dn), "w"); sys.stderr = os.fdopen(os.dup(dn), "w"); os.close(dn)
def _restore_stdio(saved):
    import sys; sys.stdout.close(); sys.stderr.close()
    os.dup2(saved[2], 1); os.dup2(saved[3], 2); os.close(saved[2]); os.close(saved[3])
    sys.stdout, sys.stderr = saved[0], saved[1]
def run_asgi_proof(date_val):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.run_asgi_proof
    # purpose: In-process ASGI proof. Suppresses app stdout.
    # inputs: date_val.
    # returns: redacted proof dict.
    # side_effects: OS fd redirection.
    # emitted_logs: none.
    # error_behavior: raises ProofFailure or PipelineUnavailable.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.run_asgi_proof
    import asyncio, sys
    from httpx import ASGITransport, AsyncClient
    saved = (sys.stdout, sys.stderr, os.dup(1), os.dup(2))
    _silence_stdio()
    try:
        from app.main import app
        t = ASGITransport(app=app, client=("127.0.0.1", 65432))
        async def _run():
            async with AsyncClient(transport=t, base_url="https://127.0.0.1:8000") as c:
                return await request_proof(c, "asgi", date_val)
        return asyncio.run(_run())
    finally: _restore_stdio(saved)
def run_http_proof(base_url, date_val):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.run_http_proof
    # purpose: HTTP transport against already-running API.
    # inputs: base_url — API base; date_val — ISO date.
    # returns: redacted proof dict.
    # side_effects: none (HTTP client only).
    # emitted_logs: none.
    # error_behavior: raises ProofFailure(secure_cookie_requires_https) for http.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.run_http_proof
    import asyncio; from httpx import AsyncClient
    try:
        parsed_u = urlsplit(base_url); parsed_u.hostname; parsed_u.port
    except Exception: raise ProofFailure(ProofErrorCode.invalid_base_url) from None
    if parsed_u.scheme == "http":
        raise ProofFailure(ProofErrorCode.secure_cookie_requires_https)
    async def _run():
        async with AsyncClient(base_url=base_url) as c:
            return await request_proof(c, "http", date_val)
    return asyncio.run(_run())
class _FatalArgumentParser(argparse.ArgumentParser):
    """Custom parser that raises ProofFailure instead of printing to stderr."""
    def error(self, msg):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API._FatalArgumentParser.error
    # purpose: Override argparse error to raise ProofFailure.
    # inputs: msg.
    # returns: None.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ProofFailure(invalid_cli).
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API._FatalArgumentParser.error
        raise ProofFailure(ProofErrorCode.invalid_cli)
def parse_args(argv=None):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.parse_args
    # purpose: Parse and validate CLI arguments before any I/O.
    # inputs: argv — optional arg list.
    # returns: argparse.Namespace with date, out, transport, base_url.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ProofFailure on any validation failure.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.parse_args
    p = _FatalArgumentParser(description="Prove real V2 API pipeline.")
    p.add_argument("--transport", choices=["asgi","http"], default="asgi")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--date", default="2026-07-08")
    p.add_argument("--out", default="/tmp/solarsage-v2-real-api-proof.json")
    try: args = p.parse_args(argv)
    except ProofFailure: raise
    except SystemExit: raise ProofFailure(ProofErrorCode.invalid_cli) from None
    except Exception: raise ProofFailure(ProofErrorCode.invalid_cli) from None
    try: parsed_date = Date.fromisoformat(args.date); args.date = parsed_date.isoformat()
    except Exception: raise ProofFailure(ProofErrorCode.invalid_date) from None
    out = Path(args.out)
    if out.exists() and out.is_dir(): raise ProofFailure(ProofErrorCode.invalid_out_path)
    if not out.name or not out.parent or not out.parent.is_dir():
        raise ProofFailure(ProofErrorCode.invalid_out_path)
    try:
        parsed = urlsplit(args.base_url); parsed.hostname; parsed.port
    except Exception: raise ProofFailure(ProofErrorCode.invalid_base_url) from None
    if parsed.scheme not in ("http","https") or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
        raise ProofFailure(ProofErrorCode.invalid_base_url)
    return args
def emit_outcome(out_path, output):
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.emit_outcome
    # purpose: Safely write and print outcome. Handles write failures.
    # inputs: out_path — output file path or None; output — outcome dict.
    # returns: exit code (0 for pass, 1 otherwise).
    # side_effects: writes to out_path; prints JSON to stdout.
    # emitted_logs: none.
    # error_behavior: on OSError, replaces output with sanitized error.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.emit_outcome
    try:
        if out_path:
            Path(out_path).write_text(json.dumps(output, ensure_ascii=False)+"\n")
        print(json.dumps(output, ensure_ascii=False))
        return 0 if output.get("status") == "pass" else 1
    except OSError:
        safe = {"schemaVersion":"today-v2-real-api-proof.v1","status":"error",
                "date":output.get("date",""),"code":"invalid_out_path"}
        print(json.dumps(safe, ensure_ascii=False))
        return 1
def main():
    # START_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.main
    # purpose: Entry point. Parse CLI, check sidecar, run proof, emit outcome.
    # inputs: sys.argv via parse_args.
    # returns: exit code 0 for pass, 1 for error/unavailable.
    # side_effects: CLI parse, HTTP calls, file write, stdout print.
    # emitted_logs: none.
    # error_behavior: all exceptions converted to typed outcomes.
    # END_FUNCTION_CONTRACT: F-M-PROVE-TODAY-V2-REAL-API.main
    out_path = None; date_val = ""; result = None
    try:
        args = parse_args(); out_path = args.out; date_val = args.date
        check_sidecar_health()
        if args.transport == "asgi": result = run_asgi_proof(date_val)
        else: result = run_http_proof(args.base_url, date_val)
    except PipelineUnavailable as e:
        result = {"schemaVersion":"today-v2-real-api-proof.v1","status":"unavailable",
                  "date":date_val,"reason":e.reason}
    except ProofFailure as e:
        result = {"schemaVersion":"today-v2-real-api-proof.v1","status":"error",
                  "date":date_val,"code":e.code.value}
    except Exception:
        result = {"schemaVersion":"today-v2-real-api-proof.v1","status":"error",
                  "date":date_val,"code":"internal_error"}
    return emit_outcome(out_path, result)
if __name__ == "__main__": import sys; sys.exit(main())
