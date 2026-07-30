# P0-G-D — Logging guardrail discovery boundaries

Phase / Wave: `today-convergence-2 / P0-G`

Modules: `M-TOOL-OBSERVABILITY-GUARDRAILS`

## Goal

Ограничить frontend logging discovery исходным деревом: guardrail не должен
сканировать локальные Git worktrees и сгенерированные build/test artifacts.
Наблюдаемый результат — файлы под `.worktrees`, Next/build/coverage/report
каталогами гарантированно исключаются, а обычный production source остаётся в
scan.

## Exact write scope

- `scripts/check_logging_guardrails.py`

## Frozen / Out of scope

- event registry и production logging callsites;
- API/frontend/sidecar product code;
- существующие AST/PII/console policy rules;
- CI workflow;
- исключение произвольных source-каталогов ради зелёного gate.

## Must preserve

- registry drift, backend logger и Python AST gates работают без ослабления;
- frontend scan продолжает проверять обычные `.ts/.tsx/.js/.jsx` source files;
- централизованный helper/constant исключает как минимум root-каталоги
  `.worktrees`, `.next`, `.next-prod`, существующие `.next-*`, `dist`, `out`,
  `coverage`, `playwright-report`, `test-results` и `.turbo`;
- `run_self_tests()` содержит pure path assertions: artifact/worktree path
  excluded, обычный `app/.../page.tsx` not excluded;
- allowlist отдельных production paths не расширяется;
- изменение не удаляет и не suppress-ит реальные violation messages.

## Verification

```bash
python3 scripts/check_logging_guardrails.py
python3 scripts/grace_lint.py apps/api/app --quiet
```

## Expected evidence

- diff только guardrail script;
- self-tests и все logging guardrails: PASS;
- список исключённых roots и negative source assertion.

## Escalation

Если обнаружена реальная violation в source tree, не добавлять её в exclusions:
остановиться и доложить, чтобы исправить отдельным packet.

## No commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
