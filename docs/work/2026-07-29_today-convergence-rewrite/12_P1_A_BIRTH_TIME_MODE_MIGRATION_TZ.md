# P1-A — Birth-time mode persistence foundation

Phase / Wave: `today-convergence-2 / P1 (W2-S0)`

Modules: `M-AUTH-TG.models`, `M-PROFILE`

## Goal

Добавить в `user_profiles` persistence-поля режима времени рождения и
воспроизводимый backfill существующих строк. Наблюдаемый результат: старое
точное время мигрирует в `exact`, старый `NULL` — в `unknown` с dismissed
banner, а новые профили получают `unknown + dismissed=false` без догадок о
bucket.

## Exact write scope

- `apps/api/app/db/models.py`
- `apps/api/alembic/versions/0027_birth_time_mode.py`
- `apps/api/tests/test_birth_time_mode_migration.py`

## Frozen / Out of scope

- Pydantic/Profile HTTP wire fields и update validation;
- Day/Calendar/sidecar call graph;
- birth-time resolver/capabilities и local-date helper;
- snapshots/cache identity;
- frontend onboarding;
- изменение или удаление `birth_time`.

## Must preserve

- migration revision идёт строго после `0026_day_score_history`;
- additive DB columns:
  - `birth_time_mode` non-null string, allowed `exact|bucket|unknown`, server
    default `unknown`;
  - `birth_time_bucket` nullable string, если не null — только
    `night|morning|day|evening`;
  - `birth_time_prompt_dismissed` non-null boolean, server/Python default false;
- upgrade backfill: `birth_time IS NOT NULL → exact`, `birth_time IS NULL →
  unknown`; bucket всегда null; dismissed true только у мигрированных null;
- новые raw/ORM строки без новых полей получают `unknown`, null bucket, false;
- downgrade удаляет только три новых поля/constraints и сохраняет старый
  `birth_time` и остальные profile data;
- повторный upgrade после downgrade детерминированно воспроизводит backfill;
- migration работает на SQLite rehearsal и PostgreSQL-совместимом SQLAlchemy
  API (без dialect-specific raw boolean SQL);
- DB enum-like check constraints fail closed для неизвестных mode/bucket;
- compound mode/time shape пока не вводится: её атомарно валидирует Profile
  service в следующем packet, чтобы этот additive changeset не ломал legacy
  partial PUT до его переключения;
- GRACE contracts/maps `models.py` остаются истинными; новый test-файл имеет
  разметку.

## Verification

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_birth_time_mode_migration.py tests/test_alembic_roundtrip.py -q
cd ../.. && python3 scripts/grace_lint.py apps/api/app --quiet
```

## Expected evidence

- diff только трёх разрешённых файлов;
- migration test доказывает exact/null backfill, new-row defaults, invalid enum
  rejection, downgrade data preservation и second upgrade;
- generic Alembic round-trip остаётся зелёным;
- backend GRACE PASS.

## Escalation

Если текущий migration head не `0026_day_score_history`, SQLite batch требует
изменить старую migration или для результата нужен schema/API scope —
остановиться и доложить, не создавать merge head и не править соседние файлы.

## No commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
