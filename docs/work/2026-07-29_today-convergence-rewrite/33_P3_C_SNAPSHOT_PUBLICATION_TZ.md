# 33 — P3-C Atomic snapshot publication

Статус: **controller packet / implementation-ready**

Исполнитель: Codex CLI, `gpt-5.6-luna`, effort `high`

Depends on: packets 30–32, schema 0028

## 1. Локальная цель

Добавить минимальный PostgreSQL persistence boundary для уже проверенного
`TodayConvergenceSnapshotDocument`:

```text
document + authenticated owner
  -> INSERT ... ON CONFLICT DO NOTHING
  -> inserted row OR load committed winner by frozen identity
  -> one published snapshot ID
```

Параллельные foreground/pregen callers с одной identity получают один и тот же
row. Повторная публикация не мутирует deterministic JSON.

## 2. Exact write scope

- `apps/api/app/services/today_convergence_snapshot.py`
- `apps/api/app/services/today_snapshot_service.py` (new)
- `apps/api/app/core/logging_events.py`
- `lib/log/events.gen.ts`
- `grace/canon/observability.xml`
- `apps/api/tests/test_today_convergence_snapshot.py`
- `apps/api/tests/test_today_snapshot_service.py` (new)
- `apps/api/tests/test_today_snapshot_postgres.py` (new, integration)
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet

## 3. Frozen / out of scope

- не менять W1 YAML, formula/runtime, version constants, DB models, migration
  0028 или создавать новую migration;
- не добавлять API route, access projection, narrative lease/LLM, pregen,
  supersession, impression, check-in, lookahead, calendar/history или cleanup;
- не обновлять existing snapshot row и не принимать arbitrary JSON вместо
  `TodayConvergenceSnapshotDocument`;
- не использовать SQLite для concurrency proof и не делать application-level
  check-then-insert race;
- не логировать user/snapshot/profile/input hashes, raw JSON, coordinates,
  birthday, Telegram identity или DB exception text;
- не коммитить и не push.

## 4. Document storage coordinates

Добавить в frozen `TodayConvergenceSnapshotDocument` required:

```python
target_date: date
timezone: str
```

Builder заполняет их из уже validated calculation и доказывает equality с
`canonical_input_json.target`. Не извлекать эти поля обратно из mutable JSON в
persistence service. Existing deterministic/hash/privacy behavior не меняется.

## 5. Publication service contract

Новый `TodaySnapshotService(db: AsyncSession)` с public:

```python
@dataclass(frozen=True)
class TodaySnapshotPublication:
    snapshot: TodaySnapshot
    outcome: Literal["published", "conflict_reused"]

async def publish_or_load(
    self,
    user_id: UUID,
    document: TodayConvergenceSnapshotDocument,
) -> TodaySnapshotPublication

async def load_owned(
    self,
    user_id: UUID,
    snapshot_id: UUID,
) -> TodaySnapshot | None
```

`publish_or_load`:

- strict types: real UUID owner and exact document class;
- строит row только из typed document, deep-copies both JSON values;
- генерирует candidate UUID в app и выполняет PostgreSQL insert с
  `ON CONFLICT ON CONSTRAINT uq_today_snapshots_identity DO NOTHING RETURNING id`;
- identity ровно `(user_id, target_date, input_hash, formula_version,
  calculation_version, canon_hash)`;
- если inserted — загружает candidate; если conflict — загружает winner той же
  полной identity; `None` после completed statement fail-closed;
- commit принадлежит методу: row опубликован до возврата; SQLAlchemy failure
  делает rollback, sanitized `system.error`, typed
  `TodaySnapshotPersistenceError("today_snapshot:persistence")`;
- programming/type errors fail before SQL; неожиданные non-SQL errors не
  маскируются;
- не retry, не second calculation, не update/upsert deterministic fields.

`load_owned` выполняет один `SELECT ... WHERE id=:id AND user_id=:owner`.
Чужой и отсутствующий row одинаково дают `None`; никаких existence details.

Через service API immutable означает:

- повтор с той же identity, но подменённым result JSON возвращает original
  winner без UPDATE;
- mutation caller-owned dict после publish не меняет DB JSON;
- сервис не содержит update/delete methods.

DB-level trigger и supersession rules придут отдельным lineage packet; этот
срез доказывает immutable publication path, не произвольный direct SQL.

## 6. Structured logging registry

Добавить в source registry `grace/canon/observability.xml` и синхронно в два
generated unions:

- `day.snapshot_published` — payload `state`, `birth_time_mode`;
- `day.snapshot_conflict_reused` — payload `state`, `birth_time_mode`;
- `day.snapshot_lookup_hit` — payload `lookup=owned_id`;
- `day.snapshot_lookup_miss` — payload `lookup=owned_id`.

Owner: `W-TODAY-CONVERGENCE-W3`. Service перед каждым событием binds exact
`slice=W-TODAY-CONVERGENCE`, `module=M-TODAY-SNAPSHOT-SERVICE`,
`block=PUBLISH|LOAD_OWNED`. Logging failure не меняет DB outcome по общему
logger contract. SQL failure использует existing `system.error` только с
`error={"type": <exception class>}`; raw message/statement/params запрещены.

## 7. Tests

### 7.1 Unit / source

1. document exposes typed target date/timezone and canonical target equality;
2. invalid owner/document fail before any session call;
3. row values copy every schema field exactly and deep-copy JSON;
4. source contains PostgreSQL `on_conflict_do_nothing` and no pre-check/update/
   retry/legacy/LLM path;
5. four event names exist 1:1 in XML/Python/TS; logging guardrails pass;
6. load query contains owner + ID and logs hit/miss without raw IDs;
7. SQLAlchemy error rollback + sanitized `system.error` + typed failure;
8. unexpected programming error propagates.

### 7.2 PostgreSQL integration

`test_today_snapshot_postgres.py` is marked `integration`, requires
`TODAY_TEST_POSTGRES_URL`, fails closed if missing/non-PostgreSQL, and creates a
unique temporary schema with only `users` + `today_snapshots`; teardown drops
that exact schema.

Prove with real independent sessions:

1. two concurrent `publish_or_load` calls -> one `published`, one
   `conflict_reused`, same snapshot UUID, row count 1;
2. stored `published_at` non-null and all deterministic/lineage fields exact;
3. re-publish same identity with mutated deterministic result returns same ID
   and stored original JSON;
4. mutate caller document JSON after publish -> fresh session still reads
   original JSON;
5. owner load hit; different owner and random ID both `None`;
6. same date but changed input hash publishes a second distinct row.

Тест не использует production/dev tables: только temporary schema. Ordinary
suite по-прежнему идёт с `-m 'not integration'`.

## 8. GRACE and gates

- full GRACE module/function contracts, `owned_tests` for new service/tests;
- registry drift and logging guardrail check;
- graph module `M-TODAY-SNAPSHOT-SERVICE`; replace premature direct
  runtime→schema publication edge with document→service→schema;
- W3 publication UC explicitly claims PostgreSQL concurrency but not
  supersession/impression/check-in.

Commands:

```bash
git diff --check
cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_snapshot.py \
  tests/test_today_snapshot_service.py -q
cd ../.. && /opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check --no-cache \
  apps/api/app/services/today_convergence_snapshot.py \
  apps/api/app/services/today_snapshot_service.py \
  apps/api/tests/test_today_convergence_snapshot.py \
  apps/api/tests/test_today_snapshot_service.py \
  apps/api/tests/test_today_snapshot_postgres.py
python3 scripts/check_logging_guardrails.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
```

Targeted PostgreSQL gate:

```bash
cd apps/api && TODAY_TEST_POSTGRES_URL='<isolated PostgreSQL URL>' \
  PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_snapshot_postgres.py -q
```

## 9. Expected evidence

- RED→GREEN unit and real PostgreSQL evidence with counts;
- exact publication outcomes/one-row concurrency/immutable conflict result;
- four structured events and guardrail drift PASS;
- broad API non-integration suite remains green;
- no frozen/schema/migration diff, exact scope, no commit/push.
