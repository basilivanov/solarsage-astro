# W4-O1 TZ: bounded Today path, честный cache и retryable pregen

Дата: 2026-07-28  
Phase / Wave: **W4-TODAY-CONVERGENCE**, operational slice O1  
Родители: `21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md`,
`26_TZ_W4_C2_FOCUS_NARRATIVE.md`,
`27_TZ_W4_AMENDMENT_PUBLIC_EVENT_SELECTION.md`  
Связанный canary: `30_TZ_W4_CANARY_SANITIZED_FIXTURES.md`  
Роль: backend/infra coder + reviewer. Ничего не коммитить и не пушить — коммит
делает ревьюер.

## 1. Цель и доказанный дефект

На cache miss пользовательский `/api/day` ждёт до ~75 секунд не из-за
sidecar, а из-за orchestration boundary:

| Текущее место | Что происходит | Риск |
|---|---|---|
| `today_service.py`, LLM phase около `asyncio.wait` | одновременно стартуют legacy `headline/reading/notes/why/interpretation` | первый экран ждёт старый eager output |
| `today_service.py`, focus block после этой фазы | `generate_focus_narrative()` вызывается отдельным `await` | focus не ограничен тем же hard deadline |
| `llm_service.py`, `_openrouter_generate`/`_deepseek_generate` | каждый provider attempt имеет независимый timeout 60s; fallback последовательный | два окна могут превысить request budget |
| `_get_cached_payload`/cache gate | проверяет версии и старые advice-инварианты, но не качество `focus.contentState` | `unavailable` может выглядеть как успешный pregen/current cache |
| `day_pregen.py` | `elapsed > 1s` считается `ok`, default только `days_ahead=1`, per-user error swallowed | плохой результат отмечается как прогрев, retry/coverage не доказаны |

O1 исправляет orchestration и операционные границы. Он не меняет формулу
астрологического расчёта и не добавляет новый LLM-вызов.

## 2. Нормативные инварианты

1. **Один absolute deadline на request.** Каждая LLM operation получает
   `deadline_at`/remaining budget; локальный timeout не может продлить общий
   budget. Cancellation всегда awaited, платный запрос не остаётся в фоне.
2. **Focus находится внутри bounded phase.** Нельзя вызывать focus narrative
   после завершения `asyncio.wait` старого набора задач.
3. **Facts не зависят от LLM.** Deterministic focus/events/state строятся и
   возвращаются даже при timeout/provider error.
4. **Focus failure fail-closed.** Timeout, provider error, parse/schema/claim
   reject дают `contentState="unavailable"`, все LLM-owned поля `null` и
   ровно пользовательское сообщение «Персональный разбор пока не готов» на UI.
   Шаблонный fallback-текст для focus запрещён.
5. **Cache quality-aware.** Current cache hit разрешён только при
   `contentState=ready` для `convergence_today|single_impulses` или
   `contentState=not_needed` для `background_only|no_accent`. `pending`,
   `unavailable`, schema-invalid и отсутствующий `focus` под новой focus
   identity — cache miss/retry, не success.
6. **Одна дата — один canonical result.** Today API и pregen вызывают один и
   тот же `TodayService` с одинаковыми flags, versions, timezone и cache key.
7. **Никаких raw personal data в telemetry.** User hash допускается только в
   pregen diagnostics; Telegram ID, username, birth data, UUID и evidence не
   печатаются.

## 3. Бounded execution contract

### 3.1. Foreground phases

Разделить путь на явно измеряемые фазы:

```text
request deadline
  ├─ deterministic calculation + focus assembly
  ├─ compact focus narrative (0..1 LLM call, remaining budget)
  └─ serialization/cache write
```

Legacy `why`/длинные 12-sphere branches не должны блокировать первый usable
focus. На переходный период они могут сохраняться для совместимости старого
payload, но должны быть либо вынесены в deferred/disclosure path, либо
запущены параллельно без права продлить focus deadline. Их результат не может
перевести focus из `unavailable` в `ready`.

`TodayPayload` пока содержит обязательные legacy `headline/reading/why` поля и
кэшируется одной строкой. O1 не делает их nullable и не пишет отдельный
несовместимый focus-only row. Существующий запрет cache write для degraded
legacy branches остаётся и логически объединяется с новым focus quality gate.
Полное удаление eager legacy генерации требует отдельного wire/consumer audit;
до него O1 гарантирует общий budget и отсутствие второго последовательного
focus wait.

Минимальная требуемая политика:

- deterministic facts доступны в пределах foreground factual budget;
- `focus_narrative` присутствует в том же bounded task group/phase;
- по окончании deadline все неполные задачи отменены и собраны через
  `asyncio.gather(..., return_exceptions=True)`;
- нет второго `await generate_focus_narrative()` после deadline;
- исключение одной legacy ветки не отменяет factual focus.

### 3.2. Provider chain

`LLMService._generate_text` и provider helpers принимают remaining budget.
Разрешён максимум один fallback только если после первой ошибки остаётся
достаточное время для полного запроса и валидации. Нельзя иметь два
независимых `timeout=60s` внутри одного request.

Каждый attempt имеет отдельные connect/read/pool limits, ограниченные
`remaining(deadline_at)`. При `CancelledError` HTTP client закрывается; нельзя
проглатывать отмену и запускать следующий provider.

Focus prompt остаётся compact и structured (max output 700 tokens по C2), но
evidence передаётся секциями `convergence`/`independent` из amendment §3.5.
LLM не выбирает события, relation, order или spheres.

### 3.3. Time boundary

В prompt/evidence не строить пользовательское время из UTC через
`occurs_at.strftime("%H:%M")`. Canonical instant и IANA timezone сохраняются;
локальное отображение вычисляется deterministic formatter один раз. Если
narrative должен знать время, ему передаётся уже проверенный display value с
явной timezone, но output schema не владеет временем. `occurs_at=null` остаётся
null и не превращается в `00:00`.

## 4. Exact implementation scope

### 4.1. `apps/api/app/services/today_service.py`

- Перенести compact focus narrative в bounded LLM phase; удалить post-wait
  focus await.
- Ввести request-local `deadline_at` и передать его в LLM service; не заводить
  отдельный 60-секундный budget.
- Собрать convergence/independent evidence до вызова LLM; не передавать flat
  список, из которого модель сама угадывает relation.
- При любой focus LLM ошибке атомарно оставить facts и null LLM fields.
- Добавить quality predicate для `_get_cached_payload`/`_cache_payload` по §2.5.
  Для legacy V1 identity отсутствие focus остаётся совместимым; для новой
  focus-dependent identity это miss.
- Не менять sidecar/factor calculations.

### 4.2. `apps/api/app/services/llm_service.py`

- Расширить provider boundary remaining-budget аргументом и cancellation-safe
  cleanup.
- Убрать последовательные независимые 60s окна; retry/fallback должен иметь
  общий absolute budget.
- `generate_focus_narrative` принимает compact partitioned evidence и
  возвращает `dict | None`; invalid/empty output не превращается в copy.
- Добавить structured completion telemetry только после утверждения event names
  в logging registry/contract. Не логировать prompt/evidence/text.

Generic `_generate_text` используется не только Today. Предпочтителен
optional deadline argument с прежним поведением для непромигрированных
callers либо отдельный bounded Today wrapper. Если меняется default generic
policy, обязательны caller audit и regression tests Horary/Natal/Synastry;
нельзя незаметно сократить их timeout этим срезом.

### 4.3. `apps/api/app/schemas/today_focus.py`

Добавить schema-level invariant (Pydantic validator) и negative tests:

| `state` | Допустимый `content_state` |
|---|---|
| `convergence_today` | `ready`, `pending`, `unavailable` |
| `single_impulses` | `ready`, `pending`, `unavailable` |
| `background_only` | `not_needed` |
| `no_accent` | `not_needed` |
| `unavailable` | `unavailable` |

Validator также проверяет `events <= 3`, `featured_spheres <= 3`, отсутствие
duplicate public IDs и непустую форму обязательных IDs. Трассировка каждого
`source_event_id`/`source_activation_id` к ledger требует внешнего контекста и
проверяется builder/integration canary из документа 30, а не Pydantic-моделью.
Нельзя ослаблять схему ради старого fixture; старый payload читается отдельной
compatibility веткой.

### 4.4. Cache identity/version

- Новый public selection выпускается с bump `TODAY_CONTENT_VERSION`; prompt
  version bump только если меняется prompt/schema.
- `cache_key_service.py` остаётся единственным builder identity; не добавлять
  скрытый env-флаг, который не входит в hash.
- Текущий `TODAY_CONTENT_VERSION` общий для V1/V2/V2.1/V2.2 runtime families,
  поэтому bump создаёт miss во всех выбранных families, а не только в новом
  focus UI. Rollout обязан prewarm фактически используемые identities. Разделять
  content version по family или удалять V1 — отдельная migration, не O1.
- Старые rows не удаляются и не перезаписываются новым смыслом. Current read
  использует только exact identity и quality predicate.
- Cache hit и fresh build обязаны давать одинаковые focus state, event IDs,
  null-safe order и featured IDs.

### 4.5. `apps/api/app/jobs/day_pregen.py`

Заменить elapsed-based `ok` на типизированный outcome:

```text
cache_hit
complete
unavailable_retryable
failed_retryable
failed_terminal
skipped_ineligible
```

`complete` означает factual payload + допустимый `contentState` по §2.5;
`unavailable` никогда не считается complete. На transient provider/timeout
создаётся bounded retry с backoff/jitter и максимумом попыток. Ошибка одного
пользователя не роняет остальные, но batch summary и exit status обязаны
отражать incomplete coverage.

Job должен уметь прогревать **обе локальные даты**: current (`days_ahead=0`)
и tomorrow (`days_ahead=1`). Если CLI сохраняет один `--days-ahead`, canonical
timer запускает его дважды с тем же image/flags; нельзя считать прогретым только
завтра. Для каждой user-local date учитываются DST/IANA timezone и exact cache
identity.

Логи item/batch используют утверждённые события и поля из §7, только hashed
user key. Raw `user.id` и Telegram идентификатор в stdout/stderr запрещены.

### 4.6. Audit/runbook

`make audit-day-live` сохраняет текущий auth путь, но должен иметь sanitized
focus output/fixture mode. Audit печатает state, contentState, IDs, local time,
versions и invariant result; полный payload, profile и secrets не дампятся.
Операционная команда использует canonical Compose/orchestrator path из
`AGENTS.md`, не ручной uvicorn.

## 5. SLO и rollout gates

| Метрика | Acceptance |
|---|---|
| Cache hit `/api/day` | p95 ≤ 500 ms |
| deterministic sidecar+aggregation | p95 ≤ 2 s |
| first factual cold payload | p95 ≤ 3 s, hard ≤ 5 s |
| focus core pregen | p95 ≤ 10 s, hard ≤ 15 s |
| foreground focus calls | 0..1 |
| focus output tokens | hard ≤ 700 |
| complete local-date coverage к 06:00 | ≥99% active user/date |
| unavailable после retry window | <1% |

Если narrative пока материализуется синхронно, допустим только переходный
cold-path hard limit ≤15 s из родительского TZ. Он не считается финальным
factual SLO ≤5 s и обязан быть явно отмечен в rollout evidence; 25/60/75 s
окна недопустимы в любом режиме.

Rollout порядок:

1. Сначала код + unit/fixture tests без bump или переключения traffic.
2. На candidate image прогнать O1 contract tests и dry-run pregen current+
   tomorrow для каждой реально включённой scoring family; проверить отсутствие
   leaked tasks и provider attempts за budget.
3. Выполнить content-version bump в том же release, запустить canonical pregen
   и подтвердить coverage/complete outcomes по каждой identity family (V1/V2,
   если они ещё разрешены rollout flags).
4. Только после этого включить F1 consumer; frontend не должен читать новый
   cache row до подтверждения schema/quality.
5. При rollback вернуть старый image/identity и оставить новые rows нетронутыми;
   не читать `unavailable` как current и не смешивать новый event set со старым
   narrative.

## 6. Tests

Обязательные backend проверки:

1. Focus call стартует внутри bounded phase и не вызывается после `asyncio.wait`.
2. Slow focus provider → factual payload ≤ hard budget, `unavailable`, null
   LLM fields, no background task.
3. First provider timeout + fallback укладываются в один absolute deadline;
   второй attempt не стартует при недостаточном remaining budget.
4. Cancellation closes client and propagates `CancelledError`.
5. Invalid narrative (missing key, banned jargon, wrong event ID) атомарно
   rejected.
6. All state/contentState invalid pairs rejected by schema.
7. Current cache with `unavailable`, `pending`, missing focus or old content
   version is a miss; valid ready/not_needed is a hit.
8. Fresh build/cache hit parity for canary IDs/order/timezone.
9. Pregen retries unavailable, counts it separately, and exits non-success when
   coverage threshold is missed.
10. Pregen current+tomorrow respects two different user timezones and DST.
11. Logs contain no raw personal data and use registry-approved event names.
12. Non-Today LLM callers сохраняют прежний contract либо покрыты отдельным
    caller-audit evidence, если generic provider policy всё же изменена.

Минимальные команды после реализации:

```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/ -q -k "today_focus or pregen or cache or llm"
python -m pytest tests/ -q
```

## 7. Observability contract

Перед использованием добавить события в registry/contract (сначала registry,
потом код). Рекомендуемые имена из родительского TZ:

| Event | Безопасные поля |
|---|---|
| `day.convergence_built` | state, event_count, featured_count, duration_ms |
| `llm.call_completed` | operation, provider, model, token counts, duration, outcome, fallback_used |
| `day.pregen_item_completed` | outcome, content_state, elapsed_ms, retryable, hashed_user_key |
| `day.pregen_batch_completed` | selected, complete, cache_hit, unavailable, failed, coverage |

Каждый log envelope сохраняет `slice/module/block/event/correlation_id`. Raw
event title, evidence, prompt и profile data запрещены.

## 8. Evidence и escalation

Reviewer получает:

- before/after latency trace с разбивкой deterministic/LLM/provider;
- task cancellation proof и provider attempt count;
- cache hit/miss matrix по state/contentState/version;
- pregen batch report current+tomorrow и retry outcomes;
- sanitized audit и canary report из документа 30.

Любое расширение scope на sidecar, новую модель, второй LLM-вызов, удаление
V1/V2 cache rows или изменение production orchestrator — отдельное согласование.
