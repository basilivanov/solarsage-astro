# P1-B — Atomic profile birth-time mode wire contract

Phase / Wave: `today-convergence-2 / P1 (W2-S0)`

Modules: `M-PROFILE.schemas`, `M-PROFILE.service`, `M-PROFILE.api`,
`M-CONTRACT-REGISTRY`

## Goal

Перевести `/api/profile` на явный `exact | bucket | unknown` контракт без
неявного вывода режима из старого `birthTime`. Наблюдаемый результат: GET всегда
возвращает сохранённый режим, PUT атомарно валидирует merged state до любой
мутации, а Pydantic/OpenAPI/TypeScript/Zod остаются единым wire Source of Truth.

Новые wire-поля живут внутри существующего `birth` object:

- `birthTimeMode`;
- `birthTimeBucket`;
- `birthTimePromptDismissed`.

## Exact write scope

- `apps/api/app/schemas/profile.py`
- `apps/api/app/services/profile_service.py`
- `apps/api/app/api/profile.py`
- `apps/api/tests/test_profile_endpoints.py`
- `packages/contracts/openapi.json` — generated only
- `packages/contracts/_generated.ts` — generated only
- `packages/contracts/_generated.zod.ts` — generated only

## Frozen / Out of scope

- DB model/migration 0027 (уже frozen предыдущим packet);
- Day/Calendar, natal readiness, cache/profile hash и local-date resolver;
- frontend `lib/profile.ts`, onboarding UI и ручные wire schemas;
- Today convergence root envelope;
- изменение bucket boundaries;
- compatibility inference `birthTime present → exact`.

## Must preserve

- `ProfileWrite` остаётся partial: omitted поля не меняются, но birth-time
  комбинация проверяется после merge с persisted row и **до** мутации любого
  profile field;
- read-модель всегда отдаёт non-null mode/dismissed и nullable bucket;
- accepted shapes:
  - exact: `birthTime != null`, bucket null;
  - bucket: `birthTime=null`, bucket ровно
    `night|morning|day|evening`;
  - unknown: `birthTime=null`, bucket null;
- unknown/bucket не хранят выдуманное время;
- initial legacy-style write с `birthTime`, но без явного mode, не
  авто-конвертируется и возвращает 422;
- смена режима требует согласованного merged state: например exact→unknown
  присылает mode unknown + null time + null bucket;
- `birthTimePromptDismissed` разрешает false→true, повторный true идемпотентен,
  true→false запрещён 422;
- invalid update возвращает 422 с безопасным stable code
  `INVALID_BIRTH_TIME_STATE` и не применяет даже соседний `firstName`;
- base onboarding readiness (birthday, city, gender) не начинает требовать
  exact time;
- successful update по-прежнему invalidates Today cache;
- существующие registry events становятся реальными callsites в затронутом
  коде: `profile.viewed`, `profile.lazy_created`, `profile.updated`,
  `profile.update_failed`, `profile.cache_invalidation_requested`,
  `profile.cache_invalidated`; payload содержит только safe field names/reason
  enum, без birth values/user IDs;
- MODULE_CONTRACT/MAP/owned_tests/emitted_logs обновлены по факту;
- generated artifacts создаются только `pnpm contracts:generate`, не правятся
  вручную; frontend Zod вручную не объявляется;
- `BirthData` остаётся public read root; отдельная partial write model может
  быть nested dependency `ProfileWrite`, без обязательного добавления нового
  public registry root.

## Verification

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_profile_endpoints.py tests/test_contract_registry.py -q
cd ../.. && PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python pnpm contracts:generate
PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python pnpm contracts:check
python3 scripts/grace_lint.py apps/api/app --quiet
python3 scripts/check_logging_guardrails.py
```

## Expected evidence

- exact/bucket×4/unknown happy paths;
- invalid combination matrix, legacy-style initial write rejection, no partial
  mutation on 422, irreversible dismiss flag;
- GET empty/migrated shape содержит новые camelCase fields;
- profile and contract-registry tests PASS;
- generated diff только в трёх перечисленных artifacts, повторная генерация
  byte-clean;
- GRACE/logging gates PASS.

## Escalation

Если contract generation требует ручной frontend schema/shim edit или
валидация требует менять DB/Day/Calendar/cache hash, остановиться и доложить:
это следующий packet, а не расширение scope.

## No commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
