# Wave W0 Rework 06 Architect Review

Status: REWORK REQUIRED

Reviewed commits:
- `8cdbaa2` - regenerated baseline artifacts
- `0ac418c` - output routing / fail-fast refactor
- `d4fe025` - rework 06 report

## Findings

### P0 - Required claims gate still fails

Evidence:

```bash
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\| N/A \| N/A \| N/A \||Рекомендация временно недоступна\.|Общайся с близкими.*отнош' artifacts/audit/2026-07-08/14_claims_audit.md artifacts/audit/2026-07-08/11_final_today_payload.json; echo rg_exit=$?
```

Current result:

```text
artifacts/audit/2026-07-08/14_claims_audit.md:36:- **Stale Advice Contradiction**: "Общайся с близкими для улучшения отношений" under "avoid" verdict.
rg_exit=0
```

Impact:
- The exact gate from `18_rework_06_TZ.md` fails.
- `19_rework_06_report.md` says stale history was excluded, but the TZ did not allow excluding it. The acceptance command checks both files as-is.

Required fix:
- Remove or rephrase the historical snapshot line so it does not match `Общайся с близкими.*отнош`.
- Update `scripts/audit_today.py` live claims generation and the committed `artifacts/audit/2026-07-08/14_claims_audit.md`.
- Rerun the exact `rg` command and report `rg_exit=1`.

### P1 - Required regression tests are still missing

Evidence:
- `git diff --name-status cbfc99d..HEAD` contains no test file changes.
- Rework 06 required automated tests for:
  - missing/invalid baseline fail-fast before canonical writes and before TodayService/LLM generation;
  - live output routing only under `live/<timestamp>/`;
  - relationship practical bullet avoidance.

Impact:
- The W0 harness can regress again without failing CI.

Required fix:
- Add targeted tests. Prefer fast unit tests around small helpers factored from `scripts/audit_today.py` where possible.
- At minimum, add one test file that proves output routing/fail-fast behavior without sidecar or live LLM, and one API test for the `SemanticService.build_why_contexts` relationship bullet invariant.

### P1 - Invalid baseline is not validated before writes

Evidence:
- `scripts/audit_today.py:372-377` checks only that `11_final_today_payload.json` exists.
- JSON is loaded later at `scripts/audit_today.py:494-496`, after `debug/*` files have already been written.

Impact:
- An invalid baseline can still cause partial canonical/debug writes before failure.

Required fix:
- Load and minimally validate baseline JSON before opening DB/session and before writing `debug/*` or canonical artifacts.
- Add a regression test for invalid baseline fail-fast.

## Decision

Rework 06 is not accepted.

This should be a small follow-up: fix the claims text/generator, add the missing tests, and make baseline validation happen before any artifact writes in default mode.
