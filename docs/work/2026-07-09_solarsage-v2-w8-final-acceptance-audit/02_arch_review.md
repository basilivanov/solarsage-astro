# W8 Final Acceptance Audit Architect Review

Status: REWORK REQUIRED
Reviewed commit: d1fbac4
Date: 2026-07-09

## Findings

### P0 - W8 TZ was deleted from the working tree

Evidence:

```text
## main...origin/main [ahead 173]
 D docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/00_TZ.md
```

Impact:

- The authoritative W8 instructions are no longer present in the working tree.
- A future commit could accidentally remove the task contract.

Required fix:

- Restore `docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/00_TZ.md` from `HEAD`.
- Do not delete or rewrite the W8 TZ.

### P0 - Required W8 commands were not run, but the report marks requirements as passed

Evidence:

The W8 TZ required fresh execution of:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff -- artifacts/audit/2026-07-08
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_astronomy_oracle.py tests/test_semantic_contexts.py tests/test_today_concrete_advice_consistency.py tests/test_activation_layer_service.py tests/test_activation_schema.py tests/test_scoring_v2_service.py tests/test_scoring_v2_runtime_flags.py tests/test_today_cache_v2_key.py tests/test_today_service_v2_dual_run.py tests/test_calendar_v2_dual_run.py tests/test_today_v2_payload.py tests/test_semantic_v2_service.py tests/test_llm_claim_validator.py tests/test_today_meta_versions.py tests/test_day_endpoints.py tests/test_calendar_endpoints.py -q
cd apps/solarsage && source venv/bin/activate && python -m pytest tests -q
pnpm contracts:generate
pnpm typecheck
npx vitest run __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
```

The report does not show those commands or their outputs. Instead, it shows only a narrower pytest subset and file-existence checks.

Examples:

- `make audit-day works` is marked pass because the Makefile target exists, not because the command was run.
- `independent astronomy oracle passes` is marked pass because `scripts/audit_astronomy_oracle.py` exists, not because it passed.
- `sidecar tests` are marked pass because test files exist, not because `python -m pytest tests -q` was run.
- frontend typecheck/vitest/e2e are not shown as fresh command outputs.

Impact:

- The report cannot prove full acceptance.
- The final objective cannot be marked complete from this evidence.

Required fix:

- Run every required command from `00_TZ.md`, exactly or with a documented command-equivalent if a command is impossible.
- If a command cannot run, mark the related requirements `WEAK`, `MISSING`, or `GAP`; do not mark them pass.
- Include exact pass/fail counts and exit status evidence.

### P0 - The acceptance matrix is incomplete and uses the wrong status model

Evidence:

- The W8 TZ has 49 checklist items.
- The report totals 48 items.
- The report omitted item 49: "if any hard-rule item is missing, V2 is not default production behavior."
- The W8 TZ required exact statuses: `PROVEN`, `GAP`, `WEAK`, or `MISSING`.
- The report uses `PASS` and final verdict `ACCEPTED`.

Impact:

- The report does not comply with the audit method.
- It hides uncertainty because "PASS" is used for evidence that is only indirect.

Required fix:

- Produce a 49-row matrix.
- Use only `PROVEN`, `GAP`, `WEAK`, `MISSING`.
- Use final verdict `ACCEPTANCE_READY` only if all 49 rows are `PROVEN`; otherwise `REWORK_REQUIRED`.

### P1 - Evidence quality is too weak for broad claims

Evidence:

Multiple rows use file existence or component existence as proof of runtime behavior:

- `ActivationLayer schema stable` cites file existence, not schema validation/tests/contracts.
- technique rows cite sidecar files but do not prove API wiring or generated activation evidence.
- frontend rows cite component existence, not rendered old/V2 payload tests.
- rollout rows cite implementation files, not dual-run execution evidence and rollback behavior.

Impact:

- The report is closer to an inventory than an acceptance audit.
- It could mark incomplete behavior as accepted.

Required fix:

- For each broad behavior claim, provide command evidence or precise code+test evidence that covers the behavior.
- Where only inventory evidence exists, mark `WEAK` and state the missing proof.

### P1 - Report falsely claims no sudo usage

Evidence:

The tmux transcript shows:

```bash
sudo rm -rf /opt/solarsage-astro/docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit
```

But the report says:

```text
Sudo: NOT_USED for audit commands
```

Impact:

- This violates the W8 TZ process constraint.
- The report is not reliable as a process record.

Required fix:

- Do not use `sudo` in the rework.
- Correct the process notes: W8 initial attempt used sudo; W8 Rework 01 must not.

## Accepted Parts

- The report path is correct.
- Some gate scripts were run and appear green, but they are only a subset of the required evidence.
