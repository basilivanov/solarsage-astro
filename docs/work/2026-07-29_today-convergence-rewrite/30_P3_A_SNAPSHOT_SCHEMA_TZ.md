# 30 — P3-A Snapshot persistence schema

Статус: **controller packet / implementation-ready**

Исполнитель: Codex CLI, `gpt-5.6-luna`, effort `high`

Depends on: packet 29, `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §7,
`06_DEV_RELEASE_EXECUTION_PLAN_TZ.md` P3

## 1. Локальная цель

Добавить только additive W3 persistence schema:

```text
published deterministic snapshot
  -> versioned narrative lease/content row
  -> optional immutable EveningCheckin lineage
```

Этот пакет не публикует snapshot, не вызывает runtime/LLM и не меняет HTTP.
Он создаёт минимальную схему, на которой следующий пакет реализует атомарный
insert/load-winner, impression и check-in binding.

## 2. Exact write scope

- `apps/api/app/db/models.py`
- новый `apps/api/alembic/versions/0028_today_convergence_snapshots.py`
- новый `apps/api/tests/test_today_convergence_snapshot_schema.py`
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet

## 3. Frozen / out of scope

- не менять W1 canon, calculation/runtime, wire contracts или versions;
- не менять старые cache/Today/Calendar/check-in services и API routes;
- не добавлять repository/service, locks, insert-on-conflict, impressions,
  LLM provider, pregen, access или frontend;
- не создавать compatibility aliases к `TodayPayloadCache`/legacy schemas;
- не переносить raw Telegram/profile поля в snapshots;
- не коммитить и не push.

## 4. ORM contract

### 4.1 `TodaySnapshot`

Новая таблица `today_snapshots`, ORM class `TodaySnapshot`:

```text
id: UUID PK, Python uuid4 default
user_id: UUID NOT NULL FK users.id ON DELETE CASCADE
target_date: Date NOT NULL
timezone: String(64) NOT NULL
profile_hash: String(64) NOT NULL
input_hash: String(64) NOT NULL
canon_hash: String(64) NOT NULL
formula_version: String(64) NOT NULL
calculation_version: String(64) NOT NULL
ephemeris_artifact_id: String(128) NOT NULL
birth_time_mode: String(16) NOT NULL
birth_time_range: JSON NOT NULL
deterministic_result_json: JSON NOT NULL
canonical_input_json: JSON NOT NULL
created_at: timezone datetime NOT NULL, server now
published_at: timezone datetime NOT NULL, server now
first_day_seen_at: timezone datetime NULL
first_lookahead_seen_at: timezone datetime NULL
supersedes_snapshot_id: UUID NULL self-FK ON DELETE RESTRICT
```

Constraints/indexes:

- unique identity exactly `(user_id, target_date, input_hash,
  formula_version, calculation_version, canon_hash)` named
  `uq_today_snapshots_identity`;
- check `birth_time_mode IN ('exact','bucket','unknown')`;
- index `(user_id, target_date, published_at)` for day/history lookup;
- index `supersedes_snapshot_id`;
- no `type=replay`, draft status or mutable deterministic columns.

`published_at` is non-null because production table stores only atomically
published winners. `created_at` and `published_at` may be equal. Service-level
immutability, same-owner/date supersession and cycle validation belong to P3-B.

### 4.2 `TodaySnapshotNarrative`

Новая таблица `today_snapshot_narratives`, ORM class
`TodaySnapshotNarrative`:

```text
id: UUID PK, Python uuid4 default
snapshot_id: UUID NOT NULL FK today_snapshots.id ON DELETE CASCADE
prompt_version: String(64) NOT NULL
status: String(16) NOT NULL
content_json: JSON NULL
attempt_count: Integer NOT NULL server default 0
lease_until: timezone datetime NULL
next_retry_at: timezone datetime NULL
last_error_code: String(64) NULL
created_at: timezone datetime NOT NULL, server now
updated_at: timezone datetime NOT NULL, server now/onupdate now
```

Constraints/indexes:

- unique `(snapshot_id, prompt_version)` named
  `uq_today_snapshot_narratives_version`;
- check `status IN ('pending','ready','unavailable')`;
- check `attempt_count >= 0`;
- index `(status, next_retry_at)` for bounded retry selection.

Не добавлять provider raw response/error text. `content_json` nullability/state
matrix валидирует W6 service: схема не дублирует будущий content validator.

### 4.3 Additive `EveningCheckin` fields

Существующий unique `(user_id, target_date)` и streak-поля не менять:

```text
forecast_snapshot_id: UUID NULL FK today_snapshots.id ON DELETE SET NULL
prediction_seen_at: timezone datetime NULL
prediction_seen_surface: String(16) NULL
observed_spheres: JSON NULL
```

- check `prediction_seen_surface IS NULL OR ... IN ('day','lookahead')`;
- index `forecast_snapshot_id`;
- все четыре поля nullable для старых rows и no-impression path;
- owner/date binding и непривязывание при edit — P3-C service, не ORM hook.

Обновить `models.py` module contract/map/outputs/invariants и добавить отдельные
semantic blocks `TODAY_SNAPSHOTS_TABLE`, `TODAY_SNAPSHOT_NARRATIVES_TABLE`.
Не добавлять ORM cascade hooks или relationships, если они не нужны для схемы.

## 5. Migration 0028

- `revision = "0028_today_convergence_snapshots"`,
  `down_revision = "0027_birth_time_mode"`;
- `upgrade()` создаёт snapshot, narrative, indexes/constraints, затем additive
  check-in columns/FK/check/index;
- имена ORM и migration constraints/indexes совпадают 1:1;
- portable SQLAlchemy `JSON`/`Uuid`, без PostgreSQL-only типов: быстрый migration
  test остаётся на SQLite, отдельный PostgreSQL gate приходит в P3-B/C;
- существующие check-in rows не backfill'ятся и сохраняют `NULL` lineage;
- `downgrade()` нужен только для чистого local/CI rehearsal и удаляет в обратном
  порядке новые check-in поля, narrative и snapshot tables. Production rollback
  или удаление опубликованных snapshot rows не являются продуктовым workflow;
  никаких cleanup jobs/retention в этом пакете.

## 6. Required tests

Новый один focused module должен доказать:

1. Alembic `0027 -> head` создаёт обе таблицы и ровно четыре additive check-in
   columns, не меняя `uq_checkin_user_date`, `streak` и legacy rows;
2. table columns, nullability, defaults, FK on-delete policies, named indexes,
   unique/check constraints совпадают с §4;
3. валидный snapshot + narrative + linked check-in вставляются;
4. duplicate snapshot identity и duplicate narrative version отклоняются;
5. invalid birth-time mode, narrative status, negative attempt count и invalid
   impression surface отклоняются;
6. narrative удаляется каскадно вместе со snapshot, check-in FK становится NULL
   при включённом SQLite `PRAGMA foreign_keys=ON`;
7. новый unlinked и существовавший до migration check-in сохраняют nullable
   lineage и прежний unique/streak contract;
8. ORM metadata 1:1 соответствует migration schema, JSON columns принимают
   object/list payload, timestamps server-generated;
9. на пустых новых таблицах `head -> 0027 -> head` проходит без drift;
10. Alembic имеет один head; migration/model не импортируют legacy Today schema.

Тест не должен имитировать P3-B business invariants: published immutability,
same-owner/date supersession, cycle prevention, concurrency и ownership будут
PostgreSQL integration tests следующего пакета.

## 7. GRACE and verification

- полный GRACE header/contracts/blocks для migration/test и существенного
  `models.py` update;
- graph: DB models/migration owns snapshots + narratives + check-in lineage;
- отдельная `UC-TODAY-CONVERGENCE-W3-SCHEMA` в verification matrix;
- `owned_tests` модели включает новый schema test.

Минимальные команды:

```bash
git diff --check
cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_snapshot_schema.py \
  tests/test_birth_time_mode_migration.py \
  tests/test_checkin.py \
  tests/test_checkin_endpoints.py -q
cd ../.. && /opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check --no-cache \
  apps/api/app/db/models.py \
  apps/api/alembic/versions/0028_today_convergence_snapshots.py \
  apps/api/tests/test_today_convergence_snapshot_schema.py
python3 scripts/grace_lint.py apps/api/app/db/models.py
bash scripts/grace/check-markers.sh
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/alembic heads
```

## 8. Expected evidence

- exact schema/constraint/index/FK list;
- migration roundtrip and existing check-in preservation;
- focused pytest count, Ruff, GRACE, markers, diff-check, one Alembic head;
- exact changed paths; no commit/push.
