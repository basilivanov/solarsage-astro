# Wave W0 Rework 07 Architect Review

Status: REWORK REQUIRED

Reviewed commits:
- `7e5c2ee` - claims gate fix, baseline validation, regression tests
- `756a2a2` - whitespace cleanup
- `df01ad3` - rework 07 report

## Findings

### P1 - Live isolation regression test does not enforce the required invariant

Evidence:
- `apps/api/tests/test_astronomy_oracle.py:280-306` adds `test_audit_live_isolates_output`.
- The test accepts subprocess failure:
  - if `scripts/audit_today.py --live-llm-sample` exits non-zero, the test still passes.
- The test allows a canonical root `debug/` directory:
  - `assert child.name in ("11_final_today_payload.json", "live", "debug")`
- The test runs the real audit script through subprocess and may depend on live sidecar/LLM/runtime state, even though the TZ asked for fast isolated tests.

Impact:
- This does not protect the live routing invariant from regression.
- A future change could recreate canonical `debug/` in live mode or break live execution, and this test could still pass.

Required fix:
- Replace or strengthen this test so it is deterministic and actually fails on root/debug writes.
- Preferred architecture: factor a small pure helper from `scripts/audit_today.py`, for example:
  - `resolve_audit_output_dirs(out_dir: Path, live_llm_sample: bool, timestamp: str | None = None) -> AuditOutputDirs`
  - return `root_dir`, `debug_dir`, `baseline_path`, `is_live`
- Unit-test that helper:
  - default mode: `root_dir == out_dir`, `debug_dir == out_dir / "debug"`;
  - live mode: `root_dir == out_dir / "live" / <timestamp>`, `debug_dir == root_dir / "debug"`;
  - live mode must not return or create `out_dir / "debug"`.
- If keeping a subprocess/integration test, it must:
  - fail when the subprocess fails for any reason;
  - assert there is no canonical root `debug/`;
  - assert no root `00_*` through `15_*` files are created/modified outside the live timestamp directory.

## Decision

Rework 07 is not accepted yet.

The production code and gates look close, but W0 requires regression coverage, not only manual shell verification. This should be a small test-only follow-up unless factoring the pure helper requires a small script edit.
