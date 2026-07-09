# W6 Architect Accept

Status: ACCEPTED
Branch: main
Accepted HEAD: f7bd717

## Scope Accepted

W6 Semantic/LLM evidence + frontend V2 is accepted after Rework 02.

Accepted behavior:

- `/day` can expose optional backend-owned `v2` payload when V2 frontend flag is enabled.
- V2 semantic/evidence blocks are built from `ActivationLayer` and `ScoringV2Result`.
- Concrete advice rows can carry activation/contribution evidence.
- LLM concrete advice and why-section prompts receive deterministic evidence packets.
- Frontend renders V2 evidence, technique chips, why-today, dev audit drawer, and visual mock baseline without client-side astrology.
- Frontend adapter validates present V2 payloads through `TodayV2BlockSchema.parse(apiV2)` and does not fabricate required backend-owned evidence.
- V1/old payloads still adapt with `payload.v2 === null`.

## Verification

Fresh verification on accepted HEAD:

```text
pnpm contracts:generate
exit 0

pnpm typecheck
exit 0

cd apps/api && source .venv/bin/activate && python -m pytest tests/test_semantic_v2_service.py tests/test_today_v2_payload.py tests/test_llm_claim_validator.py tests/test_llm_service.py tests/test_today_concrete_advice.py tests/test_today_meta_versions.py tests/test_day_endpoints.py -q
47 passed, 1 warning

npx vitest run __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx
60 passed

E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
1 passed

python3 scripts/check_logging_guardrails.py
All guardrails PASSED

git show --check HEAD
clean

git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
clean
```

## Notes

- Push/deploy were not attempted by W6.
- Untracked local files remain ignored: `.grace/`, `docs/superpowers/...`, `grace.db`, `skills/`.
