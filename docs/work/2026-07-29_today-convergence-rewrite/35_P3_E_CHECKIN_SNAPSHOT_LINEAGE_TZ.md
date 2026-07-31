# Packet 35 — P3-E: snapshot-linked evening check-in

Статус: **READY FOR IMPLEMENTATION**
Phase / Wave: **P3 / W3 — persistence and live-validation lineage**
Controller: `06_DEV_RELEASE_EXECUTION_PLAN_TZ.md` §P3
Normative contract: `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §7.3

## 1. Modules

- `M-CHECKIN-SERVICE`
- `M-SCHEMAS-CHECKIN`
- `M-API-CHECKIN`
- `M-TODAY-SNAPSHOT-SERVICE` / `TodaySnapshot` read boundary
- `M-OBSERVABILITY-LOGGING`
- `M-CONTRACTS`
- `M-GRACE-VERIFICATION-MATRIX`

## 2. Goal

При **первом** создании `EveningCheckin` сервер сам связывает запись с реально
показанным published snapshot того же owner/date. Показ на поверхности `day`
имеет приоритет над `lookahead`; если показа не было, lineage остаётся null.
Обычное редактирование check-in меняет ответы пользователя, включая один
опциональный `observedSpheres[]`, но никогда не перепривязывает и не
дорисовывает первоначальную prediction lineage.

Клиент не передаёт `forecastSnapshotId`, timestamp или surface.

## 3. Exact write scope

Разрешены только:

- `apps/api/app/schemas/checkin.py`
- `apps/api/app/services/checkin_service.py`
- `apps/api/app/api/checkin.py`
- `apps/api/app/core/logging_events.py`
- `apps/api/tests/test_checkin.py`
- `apps/api/tests/test_checkin_endpoints.py`
- `apps/api/tests/test_checkin_snapshot_lineage.py` (new)
- `apps/api/tests/test_checkin_snapshot_lineage_postgres.py` (new)
- `packages/contracts/openapi.json` (generated only)
- `packages/contracts/_generated.ts` (generated only)
- `packages/contracts/_generated.zod.ts` (generated only)
- `lib/log/events.gen.ts`
- `grace/canon/observability.xml`
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet-файл

Если генератор контрактов требует менять иной hand-written shim — стоп и
доложить; не расширять scope молча.

## 4. Frozen / out of scope

- не менять W1 canon, formula/calculation versions и deterministic pipeline;
- не менять migrations/models: additive W3-поля уже созданы в migration 0028;
- не менять impression endpoint и его timestamp semantics из Packet 34;
- не реализовывать Yesterday forecast recap — это P4/W5 consumer;
- не менять frontend, streak-алгоритм, `(user_id, target_date)`, mood/accuracy/
  energy/tags/note semantics;
- не добавлять per-sphere polarity/intensity matrix;
- не принимать snapshot identity или timestamp от клиента;
- не связывать Telegram `DayFeedback`;
- не переносить legacy Today/V1/V2/V2.1/V2.2 поля в новый контракт;
- не коммитить и не пушить — это делает reviewer.

## 5. Wire contract

`CheckinCreate` получает только одно новое опциональное поле:

```text
observedSpheres?: CanonicalSphere[] | null
```

Использовать **новый** `CanonicalSphere` из
`app.schemas.today_convergence`, не `TodayV2ProductSphereKey`. Список:

```text
work, money, documents, relationships, sport, communication,
health, decisions, travel, creativity, study, shopping
```

Список уникален, максимум 12 значений; отсутствие/null означает «не ответил»,
пустой список допустим как «ничего не выбрал». Ошибочный key или дубль → 422.

`CheckinResponse` дополнительно возвращает:

```text
observedSpheres: CanonicalSphere[] | null
forecastSnapshotId: UUID | null
predictionSeenAt: datetime | null
predictionSeenSurface: day | lookahead | null
```

Pydantic остаётся source of truth; после изменения выполнить штатную генерацию
трёх `packages/contracts/*` артефактов. Generated-файлы вручную не править.

## 6. Lineage selection

Только когда строки check-in ещё нет:

1. найти published `TodaySnapshot` того же `user_id` и `target_date`, у которого
   `first_day_seen_at IS NOT NULL`;
2. если найден хотя бы один — выбрать его независимо от наличия lookahead;
3. иначе искать того же owner/date с `first_lookahead_seen_at IS NOT NULL`;
4. внутри одной surface выбирать детерминированно: соответствующий
   `first_*_seen_at DESC`, затем `published_at DESC`, затем `id DESC`;
5. скопировать snapshot ID, фактический first-seen timestamp и surface в новую
   строку check-in;
6. если кандидата нет — записать все три lineage-поля null.

При update существующей строки **не выполнять rebinding**. Это включает legacy
строку с тремя null: более поздний impression и повторный submit не должны её
backfill-ить. `observed_spheres` и обычные ответы при update меняются штатно.

## 7. Must-preserve invariants

- выбранный snapshot имеет `snapshot.user_id == authenticated user` и
  `snapshot.target_date == checkin.target_date` по самому SQL predicate;
- используется только published snapshot с server-written impression;
- `day` всегда приоритетнее `lookahead`, даже если lookahead timestamp новее;
- response отражает сохранённую lineage, а не пересчитывает её при чтении;
- edit сохраняет исходные `forecast_snapshot_id`, `prediction_seen_at`,
  `prediction_seen_surface` byte/value-identically;
- no impression → все три nullable;
- существующие записи, streak и unique constraint не ломаются;
- `mood` остаётся резонансом дня, не полярностью сферы;
- логи не содержат raw Telegram/profile/note/tags/snapshot UUID/user UUID.

## 8. Structured logs

Добавить в registry, backend/frontend generated event union и observability
canon события owner `W-TODAY-CONVERGENCE-W3`:

- `checkin.lineage_bound` — первый submit связан; payload только
  `{surface: "day"|"lookahead"}`;
- `checkin.lineage_absent` — первый submit без показанного snapshot; payload
  `{reason: "no_impression"}`;
- `checkin.lineage_preserved` — update не меняет первоначальную lineage; payload
  `{has_lineage: boolean}`.

В `CheckinService` использовать существующий backend `log_event`/`log_block` и
точные `slice/module/block`. Ошибка логирования не ломает submit.
`checkin.submitted` остаётся в API и не дублирует prediction identity.

## 9. Required tests

### Unit / API

- schema принимает все 12 canonical keys, null и `[]`;
- unknown key, duplicate и 13 элементов → 422/ValidationError;
- response сериализует новые поля в camelCase;
- no impression → новый check-in с тремя null;
- lookahead-only → surface/lookahead timestamp copied;
- day + lookahead → day выбран, даже если lookahead новее;
- несколько day candidates → deterministic ordering из §6;
- edit после другого/нового impression сохраняет исходную lineage;
- legacy check-in с null lineage остаётся null при edit;
- `observedSpheres` обновляется без изменения streak/lineage;
- exact structured-log event и payload для bound/absent/preserved;
- существующие check-in endpoint/streak tests остаются зелёными.

### Real PostgreSQL integration

В отдельном opt-in модуле через `TODAY_TEST_POSTGRES_URL`, с уникальной временной
schema и гарантированным cleanup:

- snapshot → day impression → first check-in даёт SQL join по owner/date и
  сохраняет formula version + predicted selected spheres из deterministic JSON;
- day приоритетнее lookahead;
- edit сохраняет initial lineage;
- no impression оставляет linkage null;
- чужой owner/date никогда не выбирается.

Не копировать snapshot selected spheres в check-in: integration-test доказывает
их восстановление join-ом из immutable `deterministic_result_json`.

## 10. Verification commands

```bash
cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python \
  -m pytest tests/test_checkin.py tests/test_checkin_endpoints.py \
  tests/test_checkin_snapshot_lineage.py -q

cd apps/api && TODAY_TEST_POSTGRES_URL="$DATABASE_URL" PYTHONPATH=. \
  /opt/solarsage-astro/apps/api/.venv/bin/python \
  -m pytest tests/test_checkin_snapshot_lineage_postgres.py -q

PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python \
  PYTHONPATH=apps/api:packages/py-contracts pnpm contracts:generate
PYTHON=/opt/solarsage-astro/apps/api/.venv/bin/python \
  PYTHONPATH=apps/api:packages/py-contracts pnpm contracts:check

cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python \
  -m ruff check --no-cache app/schemas/checkin.py \
  app/services/checkin_service.py app/api/checkin.py \
  tests/test_checkin.py tests/test_checkin_endpoints.py \
  tests/test_checkin_snapshot_lineage.py \
  tests/test_checkin_snapshot_lineage_postgres.py

python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

Reviewer после focused gates запускает broad API `-m 'not integration'` и
повторяет real PostgreSQL gate с canonical dev DB URL.

## 11. Expected evidence and escalation

Отчёт кодера должен перечислить изменённые файлы, выбранную SQL ordering,
generated-contract diff, exact log payloads и результаты focused/PG/contract/
Ruff gates.

Если требуются новая migration, изменение `TodaySnapshot`/impression semantics,
Yesterday/frontend, произвольная target-date policy либо соседний контракт —
**стоп, доложить reviewer и запросить новый packet**. Scope не расширять.

Ничего не коммитить и не пушить — коммит делает reviewer.
