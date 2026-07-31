# 34 — P3-D Snapshot lineage and impressions

Статус: **controller packet / implementation-ready**

Исполнитель: Codex CLI, `gpt-5.6-luna`, effort `high`

Depends on: packets 30–33, schema revision 0028

## 1. Локальная цель

Закрыть оставшиеся deterministic-lineage инварианты W3 до check-in и LLM:

```text
published snapshot
  -> optional same-owner/same-date superseding snapshot
  -> first real day/lookahead impression
  -> immutable deterministic row with auditable exposure timestamps
```

Срез добавляет DB guard, service methods и единственный authenticated HTTP
endpoint `POST /api/day/snapshots/{id}/impression`. Check-in сам пока не
создаётся и narrative lease не реализуется.

## 2. Exact write scope

- `apps/api/alembic/versions/0029_today_snapshot_lineage_guards.py` (new)
- `apps/api/app/db/models.py` — только metadata индекса supersession
- `apps/api/app/services/today_snapshot_service.py`
- `apps/api/app/schemas/today_convergence.py`
- `apps/api/app/api/today_convergence.py` (new)
- `apps/api/app/main.py` — только mount нового router
- `apps/api/app/core/logging_events.py`
- `lib/log/events.gen.ts`
- `grace/canon/observability.xml`
- focused unit/API/PostgreSQL/migration tests этого среза
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet

## 3. Frozen / out of scope

- не менять W1 YAML, formula/runtime, calculation versions, migration 0028,
  legacy Day service/schema/routes или snapshot document/hash;
- не добавлять Today response endpoint, drilldown, Calendar/history,
  check-in mutation/linkage, narrative/LLM, pregen или frontend;
- impression request не принимает user ID, timestamp, target date или timezone;
- не хранить отдельную impression table: используются frozen first-seen columns;
- не логировать raw UUID/hash/JSON/profile/Telegram data или DB exception text;
- не коммитить и не push.

## 4. PostgreSQL lineage guard (revision 0029)

Revision строго после 0028 и не меняет существующие данные.

1. Заменить обычный `ix_today_snapshots_supersedes_snapshot_id` на partial
   unique index для non-null parent. Один snapshot имеет максимум одного direct
   successor; chain разрешён, fork запрещён. ORM metadata синхронизировать.
2. PostgreSQL trigger на INSERT с `supersedes_snapshot_id IS NOT NULL` обязан
   reject parent другого owner или другой `target_date`. Отсутствующий parent
   остаётся обычным FK failure. Self/cycle невозможен: parent уже существует,
   PK/FK immediate, fork закрыт unique index; это явно доказать тестом.
3. PostgreSQL BEFORE UPDATE guard:
   - deterministic/identity/lineage columns, `created_at` и `published_at`
     неизменяемы;
   - `first_day_seen_at` и `first_lookahead_seen_at` допускают только
     `NULL -> non-NULL` либо exact no-op; перенос/очистка запрещены;
   - обе first-seen колонки разрешено заполнить независимо.
4. Downgrade удаляет trigger/function, возвращает non-unique index и не удаляет
   строки/tables/columns.

Migration test идёт на real PostgreSQL temporary schema и делает
upgrade 0028→0029→0028 либо эквивалентный function/index rehearsal без доступа
к public/dev tables. SQLite не считается доказательством trigger semantics.

## 5. Service contract

Расширить `TodaySnapshotService` двумя операциями.

### 5.1 Supersession

```python
async def publish_superseding(
    self,
    user_id: UUID,
    document: TodayConvergenceSnapshotDocument,
    supersedes_snapshot_id: UUID,
    *,
    observed_at: datetime | None = None,
) -> TodaySnapshotPublication
```

- strict UUID/document/aware-datetime types до SQL;
- parent загружается owner-scoped; missing/foreign имеют один typed reason;
- parent date == document target date, timezone валиден;
- прошлый день по timezone документа supersede-ить нельзя; today/future можно;
- parent обязан быть текущей головой chain: существующий child запрещает новый
  fork, кроме idempotent reuse той же полной identity/того же child;
- insert использует тот же atomic PostgreSQL conflict path, но candidate сразу
  несёт immutable `supersedes_snapshot_id`;
- conflict winner обязан иметь тот же requested parent, иначе fail closed;
- не update старого/new row и не пересчитывать document.

Разрешено вынести общий private publication primitive, но публичный
`publish_or_load` packet 33 сохраняет семантику `supersedes_snapshot_id=NULL`.

### 5.2 Impression

```python
@dataclass(frozen=True)
class TodaySnapshotImpression:
    snapshot_id: UUID
    surface: Literal["day", "lookahead"]
    outcome: Literal["recorded", "existing"]
    seen_at: datetime

async def record_impression(
    self,
    user_id: UUID,
    snapshot_id: UUID,
    surface: Literal["day", "lookahead"],
    *,
    source_snapshot_id: UUID | None = None,
    observed_at: datetime | None = None,
) -> TodaySnapshotImpression | None
```

- owner/missing не различаются: `None`, endpoint преобразует в 404;
- `observed_at` server-owned, timezone-aware UTC-normalized; optional только для
  deterministic tests/internal caller;
- `day`: `source_snapshot_id` запрещён и snapshot target date должна совпадать
  с local date `observed_at` в stored snapshot timezone. Это не позволяет
  открыть вчерашний прогноз перед check-in и выдать его за prior exposure;
- `lookahead`: source обязателен, принадлежит тому же owner, source local date
  равна local date показа, target date = source date + 1, source state
  `quiet_day`. Это ровно derived lookahead relation будущего W5, без записи ID
  внутрь immutable result JSON;
- атомарный `UPDATE ... WHERE first_*_seen_at IS NULL RETURNING` выставляет
  только первый timestamp; повтор возвращает original timestamp/outcome
  `existing`; второй surface не стирает первый;
- SQLAlchemy failures rollback + sanitized typed persistence error; logging
  failure не меняет committed outcome.

## 6. HTTP and wire contract

В feature-prefixed schema добавить strict request:

```json
{
  "surface": "day | lookahead",
  "sourceSnapshotId": "uuid | null"
}
```

`extra=forbid` наследуется от `CamelModel`. Route:

```text
POST /api/day/snapshots/{snapshot_id}/impression -> 204
```

- auth только `require_session`; клиентские identity/time/date отсутствуют;
- malformed UUID/body → 422;
- foreign/missing snapshot, invalid day date или invalid lookahead relation →
  одинаковый public 404 без existence leak;
- valid repeat → 204 idempotently;
- router живёт отдельно от legacy `day.py` и не импортирует legacy Today types.

## 7. Structured events

Source registry + Python/TS unions:

- `day.snapshot_superseded` — `outcome=published|conflict_reused`;
- `day.impression_recorded` — `surface=day|lookahead`,
  `outcome=recorded|existing`;
- `day.impression_rejected` — `surface=day|lookahead`,
  `reason=not_found|invalid_relation`.

Owner `W-TODAY-CONVERGENCE-W3`. Exact context:
`slice=W-TODAY-CONVERGENCE`, `module=M-TODAY-SNAPSHOT-SERVICE`,
`block=SUPERSESSION|IMPRESSION`. Никаких raw IDs.

## 8. Tests and required evidence

### Unit/API

1. strict inputs fail before SQL; stored timezone/date validation fail closed;
2. supersession same owner/date today or future succeeds; cross-owner/date,
   past date, conflict with different parent and fork reject;
3. plain publish writes NULL parent; superseding publish copies all document
   fields and parent exactly;
4. day and valid lookahead first/repeat semantics; invalid/missing/foreign/date
   relations do not expose existence;
5. concurrent same-surface impression produces one `recorded`, one `existing`,
   identical first timestamp; day then lookahead preserves both;
6. HTTP auth/422/404/204 and no legacy import;
7. event parity/guardrails/sanitized error/logging-failure behavior.

### Real PostgreSQL temporary schema

- DB trigger rejects deterministic UPDATE, first-seen overwrite/clear and
  cross-owner/date parent;
- same-owner/date chain works, fork and direct cycle construction fail;
- concurrent impression and supersession behavior matches service contract;
- upgrade/downgrade guard rehearsal preserves rows and restores non-unique
  index after downgrade.

The integration module must require `TODAY_TEST_POSTGRES_URL`, reject non-PG,
create/drop an exact unique temporary schema and never address public tables.
Ordinary suite remains `-m 'not integration'`.

## 9. GRACE and gates

- complete module/function contracts and `owned_tests`;
- graph adds feature API edge and lineage guard edge;
- verification matrix W3 lineage row claims only supersession/impressions;
- `git diff --check`, scoped Ruff, logging guardrails, GRACE lint, marker check;
- focused tests, real PostgreSQL tests, then broad API non-integration suite;
- exact scope check and zero diff in frozen paths.

Expected handoff: RED→GREEN evidence, focused/PG/broad counts, migration
upgrade/downgrade result, exact changed paths, no commit/push.
