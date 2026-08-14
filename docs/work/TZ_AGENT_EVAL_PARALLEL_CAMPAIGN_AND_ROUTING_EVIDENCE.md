# ТЗ: Parallel Agent Eval Campaign + Routing Evidence для SolarSage

**Статус:** implementation-ready master TZ  
**Дата:** 2026-08-14  
**Репозиторий:** `basilivanov/solarsage-astro`  
**Потребитель результатов:** `basilivanov/grace-orchestrator`

---

## 1. Цель

Нужно расширить существующий `scripts/agent_eval.py`, чтобы он мог безопасно и воспроизводимо выполнять большой eval campaign параллельно, а затем агрегировать результаты в набор метрик и versioned evidence snapshot, который Grace Orchestrator сможет использовать для model routing.

Главный вопрос кампании:

> Какая модель или routing policy быстрее, дешевле и надёжнее доводит production-похожий work packet до принятого GREEN-результата, с минимальным количеством retry/escalation и без роста critical failures?

Сравниваем не «интеллект модели вообще», а production outcome на задачах SolarSage.

Первый обязательный набор моделей:

- `luna-max` — GPT-5.6 Luna, effort `max`;
- `gemini-3.7-high` — Gemini 3.7 Flash, high reasoning/profile;
- `deepseek-v4-flash` — DeepSeek 4 Flash.

DeepSeek должен оставаться полноценным кандидатом, а не контрольной моделью: прошлые прогоны уже показали, что он может быть близок к Luna по качеству при заметно меньших time/cost.

---

## 2. Граница ответственности

### SolarSage отвечает за

1. frozen eval tasks;
2. runner и безопасную parallel execution;
3. repeat runs;
4. raw/objective evidence;
5. blind review artifacts;
6. aggregation metrics;
7. pipeline leaderboard;
8. versioned routing evidence snapshot.

### Grace Orchestrator НЕ должен проводить эти eval'ы

Grace только читает готовый evidence snapshot и применяет routing policy в runtime.

---

## 3. Что уже есть и что сохраняем

Существующий harness уже имеет правильные базовые свойства:

- каждый task pin'ит `base_sha` и `base_tree`;
- каждый candidate работает в отдельном detached worktree;
- артефакты кандидатов физически разделены;
- baseline выполняется отдельно;
- candidate failures записываются как outcomes;
- model time, verification, usage, cost, patch и scope evidence сохраняются;
- blind identity mapping отделён от scorecard;
- heavy dependencies (`node_modules`, `.venv`) подключаются ссылками из host runtime;
- runner не должен commit/push в main tree.

Эти свойства нельзя ломать ради concurrency.

---

## 4. Объём eval campaign

### 4.1. Существующие eval tasks

Обязательно прогнать текущие пять:

1. `checkin-mood-trend-v1` — full-stack slice;
2. `day-momentum-v1` — deterministic backend;
3. `grace-event-registry-v1` — canon/process discipline;
4. `ui-contract-disclosure-v1` — UI semantic/test contract;
5. `sidecar-planet-house-v1` — cross-codebase change + backward compatibility.

### 4.2. Добавить два новых eval

#### A. `repair-after-verifier-v1`

Цель: измерять способность модели не писать feature с нуля, а корректно чинить уже существующую неудачную попытку после verifier.

Вход должен включать:

- исходный task packet;
- существующий diff/implementation;
- failing test/verifier output;
- acceptance criteria.

В prepared failure должны присутствовать как минимум:

- один реальный failing test;
- одна subtle contract/behavior mistake;
- одна process/scope trap, которую нельзя «чинить» массовым переписыванием.

Задача модели:

> Довести существующую попытку до GREEN с минимально необходимым patch, не переписывая feature без причины.

Дополнительные метрики:

- repair success;
- repair wall seconds;
- additional tokens;
- additional cost;
- regressions introduced;
- patch inflation vs original failed attempt.

#### B. `discovery-refactor-v1`

Цель: проверить ситуации, где coder не получает почти готовый маршрут по файлам.

Task должен быть сформулирован на уровне проблемы, например:

- в системе дублируется вычисление/логика;
- нужно найти источники дублирования самостоятельно;
- сохранить backward compatibility/public behavior;
- минимизировать scope;
- добавить/обновить tests;
- оставить verifier GREEN.

Не давать модели полный список файлов, которые надо менять. Eval должен измерять:

- repo exploration;
- архитектурное понимание;
- scope discipline;
- correctness;
- отсутствие unnecessary rewrite.

---

## 5. Количество прогонов

Для каждого из 7 eval tasks выполнить:

- 3 модели;
- 5 независимых scored repeats на каждую модель.

Итого:

- `7 tasks × 3 models × 5 repeats = 105 candidate runs`;
- логически это `35 task/repeat batches`, если внутри batch одновременно стартуют 3 модели.

Каждый repeat должен быть самостоятельным stochastic trial с отдельным run identity и отдельными артефактами.

Нельзя использовать один patch/result несколько раз как пять повторов.

---

## 6. Parallel execution

### 6.1. Текущая проблема

Сейчас `execute_eval()` запускает candidates последовательно через цикл по `selected_models`.

Нужно сделать параллельную orchestration, сохраняя isolation contract.

### 6.2. CLI

Добавить параметры:

```bash
--jobs N
--agent-jobs N
--verification-jobs N
--repeats N
```

Предпочтительная семантика:

- `--jobs` — shorthand/общий default;
- `--agent-jobs` — глобальный максимум одновременно работающих model calls;
- `--verification-jobs` — глобальный максимум одновременно работающих verifier subprocesses;
- `--repeats` — число независимых повторов task/model matrix.

Также предусмотреть provider/runner concurrency limits через config или CLI, например:

```text
codex = 2
opencode = 4
```

Чтобы один provider не получил burst выше допустимого rate/concurrency limit.

### 6.3. Рекомендованный стартовый режим для кампании

Начальный production profile:

```text
agent_jobs = 6
verification_jobs = 2
```

И одновременно держать 3–4 task/repeat batches, если host RAM/CPU позволяет.

Значения должны быть configurable, а не hardcoded.

### 6.4. Реализация

Допустима реализация через `concurrent.futures.ThreadPoolExecutor`: тяжёлая работа выполняется внешними subprocess'ами, поэтому отдельный asyncio rewrite не обязателен.

Нужны отдельные semaphores/limiters для:

- agent subprocesses;
- verification subprocesses;
- provider/runner quotas.

### 6.5. Git worktree locking

Каждый candidate сохраняет отдельный worktree.

Но операции:

```text
git worktree add
git worktree remove
```

затрагивают общую `.git/worktrees` metadata.

Добавить process/thread-safe lock только вокруг создания/удаления worktree.

ВАЖНО: lock не должен держаться во время model execution или verification.

### 6.6. Unique run IDs

Текущий timestamp с точностью до секунды недостаточен для параллельных repeats одного task.

Run ID должен включать минимум:

- timestamp;
- task id;
- repeat number;
- random/nonce suffix.

Например:

```text
20260814t072300z-sidecar-planet-house-v1-r03-a8f21c
```

Collision должен быть практически исключён.

### 6.7. Shared dependencies

Сейчас worktree получает symlink на host `node_modules` и/или `.venv`.

Для v1 сохранить этот механизм, но изолировать writable caches на candidate/run уровне, где возможно:

- `XDG_CACHE_HOME`;
- pytest cache;
- npm/vite/tool caches;
- прочие runner-generated caches.

Добавить concurrency stress-test.

Если будет доказано, что конкретный tool пишет в shared `.venv`/`node_modules` и создаёт cross-run interference, тогда отдельно вводить per-worker dependency layer/reflink/copy-on-write. Не делать дорогие copies заранее без evidence.

### 6.8. Failure isolation

Один candidate:

- timeout;
- provider error;
- non-zero exit;
- usage parse failure;
- bad patch;

не должен отменять остальные futures.

Он должен завершиться как recorded candidate outcome.

Только controller/invariant errors могут валить batch/campaign.

### 6.9. Baseline

Baseline не нужно бессмысленно повторять перед каждым из трёх candidates одного frozen task/repeat batch.

Допустимо:

1. выполнить baseline до paid calls;
2. убедиться, что baseline GREEN;
3. после этого параллельно запускать candidates.

Для 5 repeats baseline policy должна быть явно записана в manifest. Предпочтительно baseline один раз на campaign/task/runtime fingerprint, если runtime fingerprint не изменился; либо один baseline на repeat batch для максимальной консервативности.

Нельзя запускать paid candidates при RED baseline.

---

## 7. Fairness и latency measurements

Параллелизация меняет характер latency measurement.

Нужно хранить два разных понятия:

1. `candidateAgentWallSeconds` — собственное wall time model call;
2. `campaignElapsedSeconds` — реальное elapsed campaign время.

При сравнении моделей по latency нельзя смешивать:

- очередь semaphore;
- model execution;
- verification queue;
- verification time.

Рекомендуемые поля:

```text
queued_at
agent_started_at
agent_finished_at
verification_started_at
verification_finished_at
agent_queue_seconds
agent_wall_seconds
verification_queue_seconds
verification_wall_seconds
```

Для Time-to-Green pipeline calculation использовать фактическую последовательность этапов policy, а не campaign scheduler wait.

---

## 8. Метрики

### 8.1. Основные outcome metrics

Считать по model × task-class и по модели в целом:

- `Green@1`;
- `Green@2`;
- `Shippable@1`;
- `Shippable@2`;
- critical failure rate;
- scope violation rate;
- no-result/empty-patch rate;
- verifier failure rate;
- timeout/provider failure rate;
- median quality score among GREEN patches;
- completion/accuracy distribution.

### 8.2. Time metrics

- median Time-to-Green;
- p90 Time-to-Green;
- first-attempt median agent wall time;
- repair median wall time;
- escalation wall time;
- campaign elapsed time.

### 8.3. Cost/token metrics

- cost per first attempt;
- Cost-to-Green;
- p90 Cost-to-Green;
- tokens-to-green;
- repair incremental cost;
- escalation incremental cost.

### 8.4. Repair metrics

Для `repair-after-verifier-v1` отдельно:

- repair success rate;
- repair-to-green rate;
- regression rate;
- repair patch size/inflation;
- same-model repair vs rescue-model repair.

### 8.5. Discovery/refactor metrics

Для `discovery-refactor-v1` отдельно:

- unnecessary touched paths;
- architecture/scope quality;
- successful autonomous discovery;
- correctness after verification;
- critical behavior regression.

---

## 9. Определение GREEN / shippable

Нужно формализовать машинно вычисляемый eligibility layer поверх human rubric.

Минимальный GREEN candidate:

- controller validity PASS;
- required verification PASS;
- no critical failure;
- no disallowed scope violation;
- patch non-empty, если task требует изменения;
- human quality score выше установленного threshold.

Threshold хранить versioned рядом с aggregation logic и не менять задним числом для уже опубликованной campaign.

`Shippable` может иметь более строгий threshold по Completion/Accuracy, но определение должно быть неизменным внутри campaign version.

---

## 10. Pipeline leaderboard

Существующие immutable rubrics не менять.

Поверх них построить отдельный leaderboard, который отвечает не на вопрос «кто выиграл один patch», а:

> Какая production policy даёт лучший Time/Cost/Reliability-to-Green?

Обязательно симулировать минимум:

1. `Luna only`;
2. `Gemini only`;
3. `DeepSeek only`;
4. `Gemini -> Gemini repair`;
5. `DeepSeek -> DeepSeek repair`;
6. `Gemini -> Luna rescue`;
7. `DeepSeek -> Luna rescue`;
8. `fast model -> same-model repair -> Luna rescue`;
9. task-class-aware policy, если данных достаточно.

Для simulation не предполагать iid retries.

Использовать наблюдавшиеся repeat outcomes и repair eval evidence.

---

## 11. Routing evidence snapshot

После scored campaign генерировать machine-readable versioned artifact, например:

```text
evals/routing-evidence/2026-08-14-v1.json
```

Snapshot должен содержать:

- schema version;
- campaign id;
- source commit SHA;
- tasks и task versions;
- model identifiers/profile/effort;
- number of repeats;
- runtime/dependency fingerprints;
- pricing snapshot IDs;
- GREEN/shippable definitions;
- aggregate metrics;
- per-task-class metrics;
- recommended policy candidates;
- confidence/sample-size fields;
- known limitations;
- raw result references.

Snapshot не должен содержать credentials или huge raw traces.

Grace Orchestrator должен иметь возможность читать snapshot без знания внутреннего layout `.eval-runs`.

---

## 12. Task classification для будущего routing

Для каждого eval task зафиксировать class/features, которые потом можно сопоставить production work packet:

```text
backend
frontend
fullstack
cross_codebase
contract_sensitive
canon_sensitive
discovery_required
refactor
repair
high_risk
```

Допускается multi-label classification.

Aggregation должна уметь строить metrics по этим классам.

Нельзя строить highly granular routing rule на классе с недостаточной выборкой; snapshot должен отражать sample count/confidence.

---

## 13. Human blind review

Blind review сохранить.

При repeats reviewer не должен видеть model identity до выставления quality score.

Нужно обеспечить, чтобы parallel execution никак не утекала в candidate labels/file names/provider logs, которые reviewer видит до reveal.

После reveal objective metrics можно агрегировать автоматически.

---

## 14. Campaign orchestration CLI

Нужен удобный способ запустить всю matrix campaign одной командой/скриптом.

Допустимые варианты:

```bash
python3 scripts/agent_eval_campaign.py \
  --tasks checkin-mood-trend-v1,day-momentum-v1,grace-event-registry-v1,ui-contract-disclosure-v1,sidecar-planet-house-v1,repair-after-verifier-v1,discovery-refactor-v1 \
  --models luna-max,gemini-3.7-high,deepseek-v4-flash \
  --repeats 5 \
  --agent-jobs 6 \
  --verification-jobs 2 \
  --confirm-paid-run
```

или equivalent subcommand в `agent_eval.py`.

Campaign controller обязан:

- preflight validate все tasks/models/pricing;
- проверить baseline policy;
- создать campaign manifest;
- продолжать после отдельных candidate failures;
- поддерживать resume;
- не переисполнять успешно законченный candidate при resume;
- явно помечать incomplete campaign.

---

## 15. Resume / crash recovery

Так как 105 paid runs — длинная операция, resume обязателен.

Нужно хранить state machine per candidate:

```text
PENDING
RUNNING
AGENT_DONE
VERIFIED
COMPLETED
FAILED_CONTROLLER
```

При crash:

- `COMPLETED` не запускать снова;
- stale `RUNNING` переводить в recoverable/incomplete после проверки process/worktree state;
- partial artifacts не считать scored result без terminal evidence.

Campaign manifest/state updates должны быть atomic (`tmp + rename`).

---

## 16. Provider/rate-limit behaviour

Provider throttling/429/temporary unavailable не должен автоматически считаться quality failure модели.

Разделить:

- `model_outcome_failure`;
- `infra/provider_failure`.

Для provider failures допустим controlled infra retry с bounded backoff, но такой retry не считается model repair attempt.

Количество infra retries и причина должны попасть в evidence.

---

## 17. Тесты runner'а

Добавить/обновить unit/integration tests минимум для:

- `parallel_worktrees_are_isolated`;
- `parallel_run_ids_are_unique`;
- `worktree_add_remove_is_serialized`;
- `one_candidate_failure_does_not_cancel_batch`;
- `agent_concurrency_limit_is_respected`;
- `verification_concurrency_limit_is_respected`;
- `provider_concurrency_limit_is_respected`;
- `parallel_artifacts_do_not_collide`;
- `resume_skips_completed_candidates`;
- `stale_running_state_is_recoverable`;
- `provider_failure_is_not_model_quality_failure`;
- `shared_dependency_parallel_smoke`;
- `campaign_metrics_are_deterministic_from_same_inputs`;
- `routing_snapshot_schema_validation`.

Также исправить устаревший test, который ожидает ровно две модели в `models.toml`; test не должен ломаться только из-за корректного добавления новых model entries.

---

## 18. Gemini 3.7

Добавить в `evals/models.toml` отдельный model profile для Gemini 3.7 Flash High.

Не переиспользовать ключ `gemini-3.6-high`.

Pricing entry должен быть отдельным immutable snapshot в `pricing.toml` с датой/source.

Существующие старые model/pricing entries не переписывать задним числом.

---

## 19. Acceptance criteria

Работа считается завершённой, когда:

1. текущие одиночные eval команды остаются backward compatible;
2. один batch может запускать минимум 3 candidates параллельно в отдельных worktree;
3. parallel run не создаёт collisions в artifacts/run IDs;
4. Git metadata operations защищены узким lock;
5. agent и verifier concurrency независимо ограничиваются;
6. provider limit существует;
7. `--repeats 5` создаёт пять независимых trials;
8. campaign runner поддерживает resume;
9. добавлены `repair-after-verifier-v1` и `discovery-refactor-v1`;
10. добавлен `gemini-3.7-high`;
11. можно выполнить матрицу 7×3×5 = 105 candidate runs;
12. агрегатор считает Green@1/2, shippable, TTG p50/p90, Cost-to-Green, critical/scope/no-result/provider failure rates;
13. pipeline leaderboard сравнивает single-model и repair/rescue policies;
14. создаётся versioned routing evidence snapshot;
15. test suite runner'а GREEN;
16. README описывает parallel/campaign/resume workflow.

---

## 20. Что НЕ делать

- не переносить routing runtime Grace в SolarSage;
- не заставлять Grace читать raw `.eval-runs`;
- не менять старые immutable task rubrics;
- не считать provider outage поражением модели;
- не смешивать scheduler queue time с model latency;
- не запускать candidates после RED baseline;
- не копировать `.venv/node_modules` для каждого worker без доказанной необходимости;
- не делать online self-learning/автоматическое изменение routing policy из одного production failure;
- не оптимизировать только средний benchmark score.

---

## 21. Результат

После реализации SolarSage должен уметь за один reproducible campaign получить evidence, достаточный для решения:

```text
какая модель лучше как default coder
какая лучше на конкретных task classes
когда выгоден same-model repair
когда нужно сразу эскалировать в Luna Max
какой policy даёт минимальный Time-to-Green
какой policy даёт минимальный Cost-to-Green без потери reliability
```

И отдать Grace Orchestrator один компактный versioned snapshot, на основании которого уже строится автоматический model routing.
