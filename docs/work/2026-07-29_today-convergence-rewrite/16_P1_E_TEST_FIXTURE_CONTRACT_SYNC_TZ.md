# P1-E — Sync active backend fixtures with explicit birth-time mode

Phase / Wave: `today-convergence-2 / P1 (W2-S0)`

## Goal

Обновить только активные test fixtures после принятого explicit profile wire
contract: любой happy-path payload с ненулевым `birthTime` обязан явно передать
`birthTimeMode="exact"`. Production validation не ослабляется.

Полный backend sweep перед packet:

```text
2075 passed, 21 failed, 6 skipped, 6 PostgreSQL-env errors
```

20 из 21 failures приходят после test-only profile PUT с `birthTime` без mode.
Оставшийся auth test меняет `APP_ENV` на staging, но не задаёт обязательный
deployed `GRACE_USER_SALT`, поэтому падает в correlation middleware до своей
реальной проверки.

## Exact write scope

- `apps/api/tests/integration/test_cache.py`;
- `apps/api/tests/integration/test_locked_day.py`;
- `apps/api/tests/integration/test_user_flow.py`;
- `apps/api/tests/test_llm_fallback.py`;
- `apps/api/tests/test_llm_why_sections_schema.py`;
- `apps/api/tests/test_today_concrete_advice_retry.py`;
- `apps/api/tests/test_today_focus_contract.py`;
- `apps/api/tests/test_today_llm_gather_overlap.py`;
- `apps/api/tests/test_real_today_v2_api_proof.py`;
- `apps/api/tests/test_auth_endpoints.py`;
- `scripts/prove_today_v2_real_api.py` — test/proof tooling payload only;
- этот packet-документ.

## Frozen / out of scope

- весь production код, schemas, generated contracts и migrations;
- profile negative tests, которые намеренно доказывают legacy write rejection;
- изменение ожиданий LLM/fallback tests кроме их profile setup;
- `tests/test_promo_postgres_acceptance.py`: отдельный gate требует изолированный
  `PROMO_TEST_POSTGRES_URL`, этот packet не подменяет его SQLite или dev DB;
- commits and push.

## Required behavior

- в happy-path birth payload с ненулевым `birthTime` добавить
  `birthTimeMode: "exact"` рядом с временем;
- не добавлять mode в intentional negative case
  `test_put_profile_rejects_legacy_birth_time_without_mode`;
- не менять assertions/production behavior тестов ради зелёного результата;
- hard-coded canonical profile в `test_real_today_v2_api_proof.py` обновить на
  новую explicit wire shape вместе с импортируемым test/proof tooling source
  `scripts/prove_today_v2_real_api.py`, сохраняя реальную проверку 1:1;
- в auth staging test задать через monkeypatch test-only
  `settings.grace_user_salt` длиной ≥32 до HTTP request; не менять middleware;
- никаких массовых format/rewrite изменений.

## Verification

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/integration/test_cache.py \
  tests/integration/test_locked_day.py \
  tests/integration/test_user_flow.py \
  tests/test_llm_fallback.py \
  tests/test_llm_why_sections_schema.py \
  tests/test_today_concrete_advice_retry.py \
  tests/test_today_focus_contract.py \
  tests/test_today_llm_gather_overlap.py \
  tests/test_real_today_v2_api_proof.py \
  tests/test_auth_endpoints.py -q

# Ordinary complete backend suite; dedicated PostgreSQL proof runs separately.
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  --ignore=tests/test_promo_postgres_acceptance.py

/opt/solarsage-astro/apps/api/.venv/bin/ruff check \
  tests/integration/test_cache.py \
  tests/integration/test_locked_day.py \
  tests/integration/test_user_flow.py \
  tests/test_llm_fallback.py \
  tests/test_llm_why_sections_schema.py \
  tests/test_today_concrete_advice_retry.py \
  tests/test_today_focus_contract.py \
  tests/test_today_llm_gather_overlap.py \
  tests/test_real_today_v2_api_proof.py \
  tests/test_auth_endpoints.py
cd ../..
/opt/solarsage-astro/apps/api/.venv/bin/python -m py_compile \
  scripts/prove_today_v2_real_api.py
cd apps/api
cd ../..
git diff --check
```

`scripts/prove_today_v2_real_api.py` is legacy compressed tooling with 79
pre-existing Ruff violations outside this packet. Reformatting the whole script
is deliberately out of scope; its one-field fixture change is guarded by
`test_real_today_v2_api_proof.py` and the compile check above.

## Expected evidence

- focused failed set becomes green without production diff;
- ordinary complete backend suite has zero failures/errors;
- exact scope contains test fixtures + this packet only;
- PostgreSQL six-test gate remains explicitly pending, not reported as pass;
- coder does not commit or push.

## Reviewer acceptance evidence

- focused packet suite: `94 passed, 1 skipped`;
- ordinary backend suite excluding the dedicated PostgreSQL module:
  `2096 passed, 6 skipped`;
- isolated migrated PostgreSQL acceptance database:
  `6 passed` (`test_promo_postgres_acceptance.py`);
- GRACE lint and logging guardrails: PASS.

## Escalation

Если после fixture sync тест падает по своей бизнес-семантике (например,
запрещённому fallback), не переписывать ожидания и не трогать production:
зафиксировать точный remaining failure для соответствующей W6/W9 волны.
