# P0-G-A — Backend GRACE self-test baseline

Phase / Wave: `today-convergence-2 / P0-G`

Modules: `T-GRACE-LINT`, `M-TOOL-GRACE-LINT`

## Goal

Сделать backend GRACE self-tests согласованными с действующей политикой
`AGENTS.md`: обязательная module-разметка и pairing проверяются автоматически,
а `FUNCTION_CONTRACT` требуется только для нетривиальных публичных функций и не
может fail-closed определяться текущим механическим линтером; backend file-length
gate также намеренно отключён. Наблюдаемый результат — self-test suite зелёный
без изменения production linter policy.

## Exact write scope

- `scripts/test_grace_lint.py`

## Frozen / Out of scope

- `scripts/grace_lint.py` и его действующая policy;
- frontend GRACE tooling;
- API/sidecar product code;
- logging registry, pregen и CI wiring;
- любые массовые правки GRACE-маркеров.

## Must preserve

- GRC001/002/003/004/020 и GRC031 positive/negative coverage;
- `AI_HEADER`, module contracts/maps, blocks и `owned_tests` самого test-файла;
- тесты не должны утверждать, что отключённые GRC010/GRC011/GRC030 активны;
- изменение должно объяснять policy-причину, а не просто удалять падающие
  assertions без замены.

## Verification

```bash
python3 scripts/test_grace_lint.py
python3 scripts/grace_lint.py apps/api/app --quiet
```

## Expected evidence

- точный diff `scripts/test_grace_lint.py`;
- количество прошедших self-tests;
- `grace_lint: PASS` для `apps/api/app`.

## Escalation

Если для исправления требуется включить новые lint rules или менять
`scripts/grace_lint.py`, остановиться и доложить: это отдельное owner/policy
решение и новый packet.

## No commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
