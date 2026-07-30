# P0-G-E — Blocking GRACE gates in CI

Phase / Wave: `today-convergence-2 / P0-G`

Modules: `M-CI-WORKFLOW`

## Goal

Подключить уже зелёные backend/frontend GRACE self-tests и marker linters к
GitHub CI как blocking step. Наблюдаемый результат — любой push/PR с нарушением
API или frontend GRACE-контракта падает в обязательном `backend-lint` job;
существующий logging guardrail остаётся blocking в `backend-tests`.

## Exact write scope

- `.github/workflows/ci.yml`

## Frozen / Out of scope

- сами GRACE/logging linters и `scripts/guardrails.sh`;
- test/coverage thresholds и `continue-on-error` других jobs;
- sidecar legacy marker baseline;
- product code, registries, deploy workflows;
- массовая переразметка CI.

## Must preserve

- существующие Ruff/API/sidecar, backend tests, frontend, contracts и logging
  steps остаются без ослабления;
- `backend-lint` остаётся blocking (`continue-on-error` не добавляется);
- новый шаг использует существующий source-of-truth runner
  `bash scripts/guardrails.sh fast`, который запускает оба self-test suite и
  оба API/frontend marker gates;
- шаг расположен после checkout/Python setup и до Ruff, чтобы падать быстро;
- repo-wide sidecar GRACE lint не добавляется;
- MODULE_CONTRACT/MAP workflow остаются согласованными с новым gate.

## Verification

```bash
bash scripts/guardrails.sh fast
python3 -c 'import pathlib, yaml; d=yaml.safe_load(pathlib.Path(".github/workflows/ci.yml").read_text()); steps=d["jobs"]["backend-lint"]["steps"]; assert any(s.get("run") == "bash scripts/guardrails.sh fast" for s in steps); assert not d["jobs"]["backend-lint"].get("continue-on-error", False)'
python3 scripts/check_logging_guardrails.py
```

## Expected evidence

- diff только CI workflow;
- `guardrails.sh fast`: backend/frontend self-tests и marker gates PASS;
- parsed workflow содержит blocking step и существующий logging step не удалён.

## Escalation

Если новый шаг выявляет настоящий GRACE failure, не отключать и не переводить
его в warning: остановиться и вынести defect в отдельный packet.

## No commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
