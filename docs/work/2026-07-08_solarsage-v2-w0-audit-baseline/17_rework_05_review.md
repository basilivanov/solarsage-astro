# Wave W0 Rework 05 Architect Review

Status: REWORK REQUIRED

Reviewed commits:
- `ebb5538` - cold-cache deterministic baseline attempt
- `73de154` - live claims isolation fix
- `4558e8a` - rework 05 report

## Findings

### P0 - Default audit still can call live LLM and bootstrap canonical baseline

Evidence:
- `scripts/audit_today.py:454-465` still calls `TodayService(db).get_today_payload(...)` in default mode before loading the committed baseline fixture.
- `TodayService.get_today_payload` is the production path that can generate fresh LLM text on cache miss.
- `scripts/audit_today.py:482-519` freezes selected volatile fields only after the production payload has already been fetched/generated.
- If `artifacts/audit/<DATE>/11_final_today_payload.json` is missing, `baseline_path.exists()` is false and the script silently writes the freshly generated payload to canonical root via `scripts/audit_today.py:549-550`.
- `16_rework_05_report.md` explicitly documents this behavior: "The baseline fixture is created on the first `make audit-day` run".

Impact:
- Default `make audit-day` is still not cold-cache safe.
- A clean CI environment or a missing baseline can silently create a new canonical baseline from live LLM output.
- This violates the rework requirement: default audit must not call live LLM generation for volatile text in order to create root canonical artifacts, and missing baseline must fail before writes.

Required fix:
- In default mode, load and validate the committed baseline fixture before any call that can generate LLM text.
- If the baseline fixture is missing or invalid, fail fast before writing canonical files and before calling `TodayService.get_today_payload`.
- Do not use `TodayService.get_today_payload` in default mode unless it is replaced by a no-LLM/no-cache-mutation path. Prefer a deterministic projection: recompute deterministic fields, merge them into the committed baseline fixture, and keep volatile narrative text frozen.

### P0 - `--live-llm-sample` still writes canonical audit root

Evidence:
- `scripts/audit_today.py:533-544` copies `00_*` through `10_*` into `out_dir` regardless of `--live-llm-sample`.
- `scripts/audit_today.py:552-555` copies `12_scoring_oracle_comparison.json` and `13_astronomy_oracle_summary.json` into `out_dir` regardless of `--live-llm-sample`.
- `scripts/audit_today.py:619-632` still writes `15_audit_summary.md` into `out_dir` regardless of `--live-llm-sample`.
- During the agent verification, live sample changed files under `artifacts/audit/2026-07-08/debug/`, then the agent restored them. This shows live mode is still sharing canonical audit directories.

Impact:
- Live sampling is not isolated. Even if file contents often match, live mode still overwrites canonical paths and can dirty tracked artifacts whenever deterministic data changes.
- The rework requested a separate live output path and no canonical root mutation.

Required fix:
- In live mode, route all outputs to `artifacts/audit/<DATE>/live/<timestamp>/`, including debug files, oracle summaries, claims audit, and audit summary.
- Do not write or copy any `00_*` through `15_*` file, `debug/*`, or root report file under the canonical `artifacts/audit/<DATE>/` directory during live mode.
- The broad check `git diff --exit-code -- artifacts/audit/2026-07-08` must pass after live mode, without manually restoring files.

### P1 - Required regression coverage is missing

Evidence:
- `git diff --name-status 35c43f3..HEAD` contains no test file changes.
- Rework 05 required regression coverage for default cold-cache/fail-fast behavior, live sample isolation, and the `WhyThisHappens` relationship contradiction.

Impact:
- The same failure can regress immediately. The current implementation already regressed live isolation once and was only caught manually.

Required fix:
- Add targeted tests for:
  - default mode fails before canonical writes and before LLM/TodayService generation when the committed baseline fixture is missing;
  - live mode writes only under `live/<timestamp>/` and leaves the full canonical audit directory unchanged;
  - supportive day with `relationships_partnership` in avoid range does not emit the relationship outreach practical bullet.

### P1 - Relationship contradiction fix is too local and not protected

Evidence:
- `apps/api/app/services/semantic_service.py:404-409` removes the hardcoded relationship bullet only when `relationships_partnership < 2.0`.
- There is no regression test for this branch.

Impact:
- The current production artifact may be clean, but the invariant is not encoded. Future scoring threshold changes or key changes can reintroduce the contradiction.

Required fix:
- Add a test that constructs supportive day contexts with `relationships_partnership` below the avoid threshold and asserts no "Общайся с близкими ... отнош" style recommendation appears.
- Prefer a shared verdict helper or named threshold over an inline magic number if one already exists in the concrete-advice scoring path.

## Decision

Rework 05 is not accepted.

The next rework must focus on the audit harness architecture, not on narrowing shell checks. Default mode must be deterministic and LLM-free for canonical artifacts. Live mode must be completely non-destructive to the canonical audit directory.
