# Packet 36 — P3-F: persistent narrative lease

Статус: **READY FOR IMPLEMENTATION**
Phase / Wave: **P3 / W3 — persistence**
Controller: `06_DEV_RELEASE_EXECUTION_PLAN_TZ.md` §P3
Normative contracts: `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §7.2,
`05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md` §2.3–2.4

## 1. Modules

- `M-TODAY-NARRATIVE-LEASE-SERVICE` (new)
- `M-TODAY-CONVERGENCE-SNAPSHOT-SCHEMA`
- `M-OBSERVABILITY-LOGGING`
- `M-GRACE-VERIFICATION-MATRIX`

## 2. Goal

Создать один PostgreSQL persistence boundary для single-flight narrative на
`(snapshot_id, prompt_version)`. Два конкурентных worker-а не получают право на
один provider-call; истёкший lease восстанавливается; ready и cooldown
идемпотентно пропускаются; stale worker не может перезаписать результат нового
claim. Failure сохраняет `status=unavailable`, `content_json=null`, стабильный
error code и retry time — без fallback-копирайтинга.

Этот packet не вызывает LLM и не меняет публичный Today payload.

## 3. Exact write scope

Разрешены только:

- `apps/api/app/services/today_narrative_lease_service.py` (new)
- `apps/api/app/core/logging_events.py`
- `apps/api/tests/test_today_narrative_lease_service.py` (new)
- `apps/api/tests/test_today_narrative_lease_postgres.py` (new)
- `lib/log/events.gen.ts`
- `grace/canon/observability.xml`
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet-файл

## 4. Frozen / out of scope

- не менять migration 0028, ORM `TodaySnapshotNarrative` или snapshot schema;
- не менять deterministic snapshot/document/canon/formula/calculation version;
- не вызывать provider/LLM и не реализовывать prompt, validator, claim binding;
- не добавлять HTTP endpoint, `BackgroundTasks`, retry route или Today consumer;
- не реализовывать pregen cohort/concurrency limiter;
- не определять глобальный max-attempt policy: W5 orchestrator решает, когда
  больше не вызывать acquire; persistence сохраняет точный `attempt_count`;
- не добавлять message broker/queue/Redis;
- не хранить fallback text, raw exception/provider body, Telegram/profile data;
- не коммитить и не пушить — это делает reviewer.

Нужен соседний scope → стоп и escalation, не расширять packet молча.

## 5. Public service contract

Новый service экспортирует immutable dataclasses и typed exceptions:

```text
NarrativeLeaseClaim:
  narrative_id, snapshot_id, prompt_version,
  attempt_count, lease_until, outcome=created|retry|recovered

NarrativeLeaseSkip:
  narrative_id, snapshot_id, prompt_version,
  status=ready|pending|unavailable,
  reason=ready|in_flight|cooldown|exhausted,
  retry_at nullable

NarrativeLeaseCompletion:
  outcome=completed|stale

TodayNarrativeLeaseError(reason)
TodayNarrativeLeasePersistenceError(reason)
```

И класс `TodayNarrativeLeaseService`:

```text
acquire(snapshot_id, prompt_version, now, lease_duration)
  -> NarrativeLeaseClaim | NarrativeLeaseSkip

complete_ready(claim, content_json)
  -> NarrativeLeaseCompletion

complete_unavailable(claim, error_code, next_retry_at)
  -> NarrativeLeaseCompletion

load(snapshot_id, prompt_version)
  -> TodaySnapshotNarrative | None
```

Допустимо назвать dataclass поля чуть иначе, если смысл и test contract
сохраняются. `prompt_version`: nonblank ≤64. `now`, `lease_until`, retry time —
aware UTC. `lease_duration`: положительный и bounded (не более 1 часа).
`error_code`: stable machine token `[a-z0-9_.-]{1,64}`, не текст exception.
`content_json`: только уже validated JSON object (`dict`), deep-copied перед DB.

## 6. Atomic transition rules

`acquire` сначала доказывает существование **published** snapshot. Missing или
unpublished → `TodayNarrativeLeaseError("snapshot_not_published")`, narrative
row не создаётся.

Далее PostgreSQL transaction + unique `(snapshot_id,prompt_version)`:

1. row отсутствует → атомарный insert `pending`, `attempt_count=1`,
   `lease_until=now+duration`, outcome `created`;
2. `ready` + non-null object content → skip `ready`;
3. `ready` без валидного content → fail closed typed persistence error;
4. `pending`, lease в будущем → skip `in_flight`, retry_at=`lease_until`;
5. `pending`, lease null/истёк → под row lock: `attempt_count += 1`, новый lease,
   outcome `recovered`;
6. `unavailable`, `next_retry_at > now` → skip `cooldown`;
7. `unavailable`, `next_retry_at IS NULL` → skip `exhausted`;
8. `unavailable`, retry due → `pending`, clear content/error/retry,
   `attempt_count += 1`, outcome `retry`.

Создание при гонке — PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` (или
эквивалент) + committed winner. Existing-row transitions сериализуются
`SELECT ... FOR UPDATE` или эквивалентным conditional update.

Claim identity для completion: минимум narrative ID + exact `attempt_count` +
exact `lease_until`. `complete_ready`/`complete_unavailable` делают CAS только
если row всё ещё `pending` и claim identity совпадает. Невладеющий/stale claim
возвращает `outcome=stale`, не мутирует row и не выбрасывает бизнес exception.

`complete_ready` атомарно ставит `ready`, deep-copied `content_json`, очищает
lease/retry/error. `complete_unavailable` атомарно ставит `unavailable`, всегда
`content_json=null`, очищает lease, пишет stable error и nullable future
`next_retry_at` (`null` = exhausted). Невалидный content/error/retry отвергается
до SQL.

## 7. Must-preserve invariants

- deterministic `TodaySnapshot` никогда не мутирует;
- одна row на snapshot/prompt version;
- один active claim; конкурентный loser не зовёт provider;
- crash recovery возможен после lease expiry;
- старый worker не может перезаписать новый claim/ready/unavailable;
- `ready` — единственный успешный outcome и всегда имеет object content;
- `pending` не является ошибкой;
- `unavailable` никогда не содержит content/fallback text;
- attempt count начинается с 1 и растёт ровно на каждый новый claim;
- все expected SQL failures rollback; unexpected errors не маскируются;
- наружу и в логи не попадают snapshot UUID, content, prompt body, user data,
  raw provider/exception strings.

## 8. Structured logs

Добавить owner `W-TODAY-CONVERGENCE-W3` во все registry/canon поверхности:

- `day.narrative_lease_acquired` payload `{outcome: created|retry}`;
- `day.narrative_lease_recovered` payload `{outcome: expired}`;
- `day.narrative_lease_skipped` payload
  `{reason: ready|in_flight|cooldown|exhausted}`;
- `day.narrative_lease_completed` payload `{outcome: ready}`;
- `day.narrative_lease_failed` payload `{retry_scheduled: boolean}`.

Для stale completion использовать sanitized `system.error` с
`error.type="narrative_lease_stale"`, без UUID/content. Не добавлять в этом
packet `narrative_requested/ready/unavailable`: это W6 orchestration telemetry.

## 9. Required tests

### Focused unit/service

- invalid UUID/version/time/duration/content/error/retry fail до SQL;
- missing/unpublished snapshot не создаёт narrative;
- created claim имеет attempt 1 и exact lease;
- ready/in-flight/cooldown/exhausted skip truth table;
- expired pending → recovered и attempt +1;
- due unavailable → retry, clears error/retry/content, attempt +1;
- complete ready stores deep copy and clears operational fields;
- complete unavailable stores null content + error/retry;
- stale attempt/lease completion не мутирует row;
- ready-without-content fail closed;
- exact event/payload и privacy-negative assertions;
- SQL error rollback + stable persistence reason.

### Real PostgreSQL opt-in

Отдельный `TODAY_TEST_POSTGRES_URL` test module создаёт unique temporary schema,
только `User`, `TodaySnapshot`, `TodaySnapshotNarrative`, затем cleanup:

- два concurrent acquire на новом key → ровно один `created`, второй
  `in_flight`, одна row и `attempt_count=1`;
- expired claim recovery → attempt 2;
- stale first claim не завершает recovered row;
- recovered claim completes ready; repeat acquire skips ready;
- отдельный key: unavailable + cooldown → skip, due retry → attempt 2;
- missing/unpublished snapshot rejects without row.

## 10. Verification commands

```bash
cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python \
  -m pytest tests/test_today_narrative_lease_service.py -q

cd apps/api && TODAY_TEST_POSTGRES_URL="$DATABASE_URL" PYTHONPATH=. \
  /opt/solarsage-astro/apps/api/.venv/bin/python \
  -m pytest tests/test_today_narrative_lease_postgres.py -q

cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python \
  -m ruff check --no-cache \
  app/services/today_narrative_lease_service.py \
  tests/test_today_narrative_lease_service.py \
  tests/test_today_narrative_lease_postgres.py

python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

Reviewer запускает broad API `-m 'not integration'` после focused/PG gates.

## 11. Expected evidence and escalation

Отчёт: exact changed paths, SQL concurrency primitive, transition table,
CAS claim identity, sanitized log payloads, focused/real-PG/Ruff/GRACE results.

Если безопасная stale-worker защита требует новую column/lease token, не
изобретать migration внутри packet: остановиться и доказать, почему
`attempt_count + lease_until` недостаточно. Ничего не коммитить и не пушить —
коммит делает reviewer.
