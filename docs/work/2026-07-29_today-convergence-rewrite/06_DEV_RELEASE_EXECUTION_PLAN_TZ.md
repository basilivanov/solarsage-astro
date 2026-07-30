# DEV RELEASE EXECUTION PLAN TZ — Today Convergence Rewrite

Дата: 2026-07-31
Статус: **implementation controller / ready after scoped checkpoint**.
Не меняет frozen W1 formula, canon, replay fingerprint или owner-approved
частоты. Нормативные детали остаются в `00_MASTER_TZ.md`,
`04_W2_W3_RUNTIME_CONTRACT_TZ.md`,
`05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md` и
`03_W7_FRONTEND_DESIGN_TZ.md`.

## 1. Цель

Получить на `dev.astro.vasiliy-ivanov.ru` рабочий release candidate нового Day:

- реальный Telegram HMAC → API → sidecar → PostgreSQL → frontend;
- `exact | bucket | unknown` без выдуманного `12:00`;
- `convergence_today | quiet_day | unavailable` и ортогональный `dayTone`;
- immutable snapshot, impression и snapshot-linked check-in;
- Calendar, Yesterday/check-in, drilldown и nightly pregen на новом контракте;
- bounded LLM с честным `contentState=unavailable`;
- новый DOM/test contract и утверждённые visual baselines;
- старые V1/V2/V2.1/V2.2 тесты не лежат параллельной «legacy suite», а
  удаляются по staged manifest в `W9_LEGACY_REMOVAL_MANIFEST.md`.

Dev RC не означает production cutover. W8 production acceptance начинается
только после отдельной приёмки dev RC владельцем.

## 2. Что уже является baseline

### 2.1 Calculation baseline — уже frozen

Повторно подбирать формулу или частоты не нужно. Источники:

- `grace/canon/today_convergence.v1.yml`, `status: frozen_w1`;
- `CALCULATION_VERSION=ss-calc-1.3.0`;
- `analysis/W1_FREEZE_DELTA_ATTESTATION.md`;
- population replay `525 600 mode-days`, `invalid_ledger=0`;
- W1 gates: 14 calculation tests + 46 version/sect/parity tests.

Новый full ephemeris replay нужен только если меняются canon/fingerprint,
eligibility, grouping, polarity/tone или factor-domain signature. Обычная
runtime-реализация обязана пройти reference parity на frozen fixtures и probe,
но не создаёт новую продуктовую квоту.

### 2.2 Текущий test baseline репозитория

Состояние на 2026-07-31:

| Слой | Что есть сейчас |
|---|---|
| API pytest | 2 066 tests: 2 050 обычных, 13 integration, 3 benchmark |
| Sidecar pytest | 241 tests |
| Frontend Vitest | 135 файлов, около 1 351 test/it declarations |
| Contract Vitest | 14 файлов внутри frontend suite |
| Real/dev Playwright | 35 Chromium tests в 16 top-level specs |
| Mock visual Playwright | 40 Chromium tests в 11 specs, 34 PNG baselines |

`ci.yml` уже блокирует Ruff, API pytest + coverage, sidecar pytest + coverage,
frontend lint/Vitest/build, contract generation/check и TypeScript. Mypy пока
`continue-on-error` и не считается release gate. E2E и visual workflows
reusable/manual; production workflow вызывает их как blocking gates.

Существующие coverage floors не понижаются: API total 81%, changed lines 80%,
sidecar total 90%; frontend lines/statements 46%, functions 64%, branches 76%.
Для нового Today недостаточно сохранить общий процент: каждая state/access/
birth-time ветка из wire-матрицы получает явный тест.

## 3. Порядок реализации

Большие документы `03/04/05` не передаются кодеру целиком. Перед каждой строкой
ниже создаётся отдельный controller packet по `coder-loop`: одна локальная цель,
exact write scope, frozen/out-of-scope, invariants, targeted verification,
expected evidence, escalation и no-commit rule.

### P0. Immutable implementation checkpoint

Закоммитить master v1.12, `AGENTS.md`, ТЗ `03/04/05/06`, W9 manifest и audit
lineage отдельным scoped commit. Кодер получает точный SHA; dirty workspace не
является контрактом.

Этот SHA является единственным source checkpoint для dev RC: API, sidecar,
frontend, migrations и generated contracts собираются из него, смешивать файлы
из текущего dirty workspace с RC запрещено.

Gate: все нормативные файлы существуют в `git ls-tree <SHA>`, W1 canon clean,
14 + 46 frozen tests зелёные.

### P0-G. Сквозной GRACE и observability gate

Это не отдельный logging framework: используются существующие GRACE-маркеры,
event registry и логгеры из `AGENTS.md`. Требование действует для каждого
controller packet P1–P8.

Для каждого нового production-файла и каждого существенно изменённого модуля:

- есть `AI_HEADER`, `MODULE_CONTRACT`, `MODULE_MAP` и `owned_tests`; для
  нетривиальных публичных функций/блоков — их contracts/markers;
- `emitted_logs` перечисляет реальные registry event names и совпадает с
  фактическими callsites;
- изменение runtime-поведения/владения/gates синхронизирует
  `grace/verification-matrix.md`, а при новых модулях/рёбрах —
  `grace/knowledge-graph.xml`;
- новый frontend path входит в `grace/frontend.paths`; новый каталог не может
  оказаться вне marker gate по умолчанию;
- новое событие сначала добавляется в observability registry и generated
  Python/TS registries, затем используется в коде.

Структурный лог пишется на значимой границе или смене состояния, а не на каждый
из ~150 факторов и не внутри каждого цикла. Обязательные наблюдаемые переходы:

- request/calculation start, success, fail и timeout;
- snapshot hit/miss/publish/conflict и ownership rejection;
- lease acquire/skip/recover/complete/fail;
- narrative requested/ready/unavailable и validator rejection;
- pregen run start, typed per-user outcome и итоговый summary;
- impression/check-in lineage accepted/rejected;
- frontend fetch/retry/ready/error и ключевые пользовательские действия.

Каждая запись несёт `slice`, `module`, `block`, `event`, `correlation_id` и только
безопасные агрегаты/enum/latency. Raw Telegram initData, tokens, cookies, LLM
text, точные birth data и unhashed user identifiers запрещены. Ошибка логгера не
ломает пользовательский flow.

P0-G исполняется первым маленьким code changeset до P1 и делает существующие
guardrails реально исполнимыми, а не декларативными:

- self-tests `grace_lint` и `grace_front_lint` зелёные;
- logging discovery не сканирует `.worktrees`/build artifacts;
- три raw `print()` legacy `day_pregen.py` заменены registry-backed structured
  events; эти события затем сохраняются или supersede-ятся новым P5 job;
- API/frontend GRACE и logging guardrails подключены к `ci.yml` как blocking
  steps; новые convergence-sidecar файлы добавляются в тот же gate явным
  списком, не через массовую переразметку старого sidecar.

После P0-G reviewer не принимает packet без следующего evidence по затронутому
scope (в команде sidecar подставляются фактически изменённые файлы):

```bash
python3 scripts/grace_lint.py apps/api/app
python3 scripts/grace_lint.py path/to/changed_sidecar.py
python3 scripts/grace_front_lint.py
python3 scripts/check_logging_guardrails.py
```

Repo-wide sidecar marker cleanup не входит в rewrite: существующий legacy
baseline имеет старую разметку, поэтому sidecar gate запускается по точному
write scope, а каждый новый/изменённый файл обязан быть чистым. Ревьюер всё
равно сверяет смысл contracts, `owned_tests` и `emitted_logs`, потому что линтер
проверяет структуру, но не истинность комментариев.

### P1. W2-S0 — profile mode, local date и wire root

Реализовать additive profile fields/migration, единый mode-aware birth-time
resolver, `resolve_user_local_date`, новый отдельный Pydantic root и generated
feature shim. Day/Calendar переводятся с noon fallback атомарно; временный
безусловный `422` для legacy unknown-пользователей запрещён.

Обязательные тесты:

- exact/bucket/unknown и невалидные комбинации profile update;
- migration round-trip: old time → exact, null → unknown + dismissed banner;
- no executable `birth_time or "12:00"` в новом Day/Calendar call graph;
- Pydantic → OpenAPI → TS/Zod, `contracts:check`, no manual wire schema;
- local date west/east UTC, DST и explicit date против `today`.

### P2. W2-S1 — deterministic convergence pipeline

Перенести frozen canon в production path: canonical event IDs, fail-closed raw
boundary, eligibility, independent units, direct grouping, hero/main-event/
impulse selection, sphere projection и `unit → group → dayTone`.

Обязательные тесты:

- mutation fixtures 1–6;
- exact + четыре bucket + unknown;
- background не входит в group/evidence count;
- fast factor один не создаёт hero/day tone;
- `≤2` сфер на физическую группу;
- неизвестный factor/orb/event class fail-closed;
- runtime output byte/semantic parity с frozen reference на фиксированном probe.

W4 replay здесь является проверочным инструментом, а не отдельной продуктовой
фичей. Изменение W1-правил останавливает пакет и требует owner decision.

### P3. W3 — snapshots, lease, impression и check-in lineage

Добавить additive migrations и runtime из `04` §7: immutable deterministic
snapshot, narrative lease, day/lookahead impressions и snapshot-linked
EveningCheckin без изменения streak uniqueness.

Обязательные integration tests на PostgreSQL:

- concurrent insert/load-winner даёт один published snapshot ID;
- published deterministic JSON неизменяем;
- supersedes только same owner/date, без циклов;
- cross-user snapshot/drilldown/impression → 404;
- day impression приоритетнее lookahead;
- edit check-in не перепривязывает lineage;
- no impression → nullable linkage;
- migration upgrade/downgrade rehearsal без удаления protected rows.

Эти тесты не прячутся только в unit suite: нужен один отдельный Today
integration module, запускаемый в ephemeral PostgreSQL gate.

### P4. W5-S1 — API consumers

Подключить новый envelope к Day, Calendar, Readings history, sphere drilldown,
static sphere page и Yesterday/check-in. Все consumers используют generated
contracts и один local-date resolver.

Обязательные contract/integration tests:

- полная `state × contentState × access × birthTimeMode` матрица;
- preview не раскрывает event IDs/timing/LLM, locked не создаёт snapshot;
- Calendar различает `hero | ordinary | not-computed`;
- pre-submit recap скрыт, post-submit связан с показанным snapshot;
- history читает published rows и не запускает N cold calculations;
- retry idempotent, ownership 404, invalid profile/date 422.

### P5. W5-S2 — nightly pregen и concurrency

Реализовать двухступенчатый pregen только для cohort из `05` §2:
deterministic snapshot → selective LLM warm-up. Это не массовая генерация всем
зарегистрированным пользователям.

Обязательные tests/measurements:

- cohort selection exact/bucket/unknown;
- idempotent rerun и typed outcomes;
- 20 concurrent GET одного user/date → максимум один provider call;
- зависший provider не удерживает deterministic response;
- retry/cooldown/lease recovery;
- cache hit p95 <1 s; cold deterministic p95 <5 s и hard deadline 10 s.

До первого runtime deploy старый `solarsage-day-pregen.timer` на dev обязательно
остановить и отключить: он вызывает legacy `TodayService.get_today_payload` и
несёт inline `TODAY_VALENCE_V1_ENABLED=true`. Во время миграции ни старый timer,
ни старый one-shot не должны писать snapshots/cache параллельно новому runtime.

Timer остаётся disabled до bounded one-shot smoke нового job. После smoke можно
включить тот же unit name только с обновлённым source/command и без legacy
valence-флага. Production timer в этом пакете не включается.

### P6. W6 — bounded narrative

Один strict-JSON call на published snapshot/prompt version. LLM не получает
сырой ledger из ~150 факторов и не меняет calculation fields.

Обязательные tests:

- claim binding к selected sourceEventIds;
- capability gate запрещает houses/ASC/MC/lots/exact time вне exact;
- timeout/schema/claim failure → `contentState=unavailable`, LLM fields null;
- никакого template fallback copy;
- максимальный hero fixture и максимальный quiet fixture укладываются в 700
  output tokens;
- summary 220 chars passes, 221 rejects целиком без обрезки;
- LLM p95 <30 s, hard deadline 45 s.

### P7. W7 — frontend, test replacement и visual baseline

Frontend импортирует только новый generated feature contract. Реализуются 16
payload fixtures, два transport states и три Yesterday/check-in fixtures из
`03` §13. Старые UI/fixture tests удаляются атомарно с новым покрытием по W9
manifest; каталога `__tests__/legacy/` не создаём.

Обязательные gates:

- root DOM attributes из `AGENTS.md`;
- hero/quiet/unavailable × steady/supportive/mixed/tense;
- exact/bucket/unknown, full/preview/locked;
- loading/error/pending/unavailable accessibility semantics;
- onboarding banner и migrated-user suppression;
- Calendar, sphere navigator/drilldown и Yesterday recap;
- `pnpm contracts:check`, TypeScript, Vitest, axe/AA и production build.

Новый visual baseline создаётся только для ключевых состояний: hero-tense,
hero-mixed, quiet-steady, calendar three-state, navigator/drilldown,
birth-time unknown и unavailable. Desktop Chromium + iPhone 13; динамические
LLM-зоны маскируются. Baseline обновляется одним явным
`UPDATE_SNAPSHOTS=true` run, просматривается владельцем и затем снова работает
fail-closed. Старые Day V2 PNG удаляются тем же changeset.

Написанные тесты должны быть подключены к реально исполняемым entrypoints:

- `.github/workflows/visual-regression.yml` больше не вызывает удалённый
  `day-v2.spec.ts`, а запускает новый Today visual suite;
- `.github/workflows/e2e.yml` и release-команда содержат новые Today/Calendar/
  check-in specs, а не только файлы, оставшиеся от legacy Day;
- добавляется один минимальный WebKit smoke нового Today на ready/loading/error
  navigation path. Полная browser matrix не требуется; iPhone 13 на Chromium
  не считается WebKit-проверкой;
- локальная команда из документации и workflow-команда используют один и тот
  же список release specs, чтобы тест не был зелёным только локально.

### P8. DEV-RC — deploy и реальная приёмка

Dev использует его канонический systemd runtime, не production Compose:

P8 исполняется тремя отдельными controller packets, чтобы environment repair,
deploy и продуктовая приёмка не смешивались в одну неотлаживаемую операцию.

#### P8-A. Dev runtime preflight

1. `solarsage-day-pregen.timer` остановлен и disabled; старого запущенного
   `day_pregen` process/job нет.
2. Зафиксирован dev env manifest для параметров из `05` §2/§4:
   `DAY_PREGEN_*`, `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS`,
   `TODAY_LLM_ON_DEMAND_CONCURRENCY`, provider model/timeouts и `RELEASE_SHA`.
   Секреты остаются только в env и не коммитятся.
3. В dev runtime удалены/выключены legacy routing flags
   `TODAY_VALENCE_V1_ENABLED`, `TODAY_VALENCE_V1_DUAL_RUN`,
   `SOLARSAGE_V2_ENABLED`, `SOLARSAGE_V2_FRONTEND_ENABLED`; новый Today не
   зависит от них.
4. Из обоих Python runtime (`apps/api/.venv` и `apps/solarsage/venv`) импорт
   `solarsage_contracts` возвращает `ss-calc-1.3.0`. Простого изменения файла в
   `packages/py-contracts` недостаточно: package должен быть реально
   установлен/синхронизирован в обоих окружениях.
5. С dev-хоста проверена достижимость фактически настроенных Telegram,
   OpenRouter и sidecar endpoints. Проверка не печатает tokens/credentials;
   недоступный обязательный endpoint блокирует RC.

#### P8-B. Deploy и release identity

1. сохранить DB backup и выполнить additive migration/rehearsal;
2. собрать frontend в `.next-prod` строго из RC SHA;
3. передать один `RELEASE_SHA=<RC SHA>` API, sidecar и frontend;
4. restart `solarsage-api`, `solarsage-sidecar`, `solarsage-frontend`;
5. health endpoints всех трёх сервисов обязаны вернуть тот же RC SHA, sidecar
   дополнительно возвращает `calculation_version=ss-calc-1.3.0` и ожидаемую
   ephemeris identity;
6. process/port check подтверждает ровно один systemd-owned listener на 8000,
   3002 и 18091, без ручного `uvicorn`/`next start`.

`git_sha=unknown`, разные SHA между сервисами или установленный
`ss-calc-1.2.0` являются hard FAIL, даже если UI визуально открылся.

#### P8-C. Product acceptance и operational evidence

До real E2E создаётся маленький воспроизводимый acceptance cohort:

- отдельные exact, bucket и unknown профили;
- full, preview и locked access;
- фиксированные даты с frozen hero и quiet reference;
- созданные тестовые user IDs учитываются существующим E2E cleanup.

Seeder/harness использует существующий Telegram HMAC/profile flow или test
fixture setup; новый test-only API route в production runtime запрещён.

После подготовки cohort:

1. выполнить targeted smoke и real E2E без `page.route`;
2. выполнить bounded новый `day-pregen` one-shot только на acceptance cohort;
3. подтвердить cache hit повторным GET без второго provider call;
4. собрать latency, snapshot/lease и LLM counters;
5. проверить `journalctl` трёх units и pregen от момента deploy: нет crash-loop,
   необработанных exception/`system.error`, повторяющихся failed leases и PII/
   secrets в логах;
6. владелец принимает UI и новый visual baseline;
7. только после этого разрешено включить обновлённый dev pregen timer.

Минимальные real E2E dev scenarios:

1. exact user → hero или quiet → drilldown;
2. new bucket/unknown onboarding → без houses/exact time;
3. preview/locked → нет скрытых evidence;
4. invalid/hanging LLM → deterministic page + honest unavailable;
5. Calendar → Day → evening check-in → same snapshot recap;
6. quiet lookahead impression → next-day check-in lineage;
7. cross-user snapshot request → 404;
8. pregen cache hit → повторный GET без provider call.

Dev RC считается готовым только при зелёных source CI, Today integration,
new visual suite, минимальном WebKit smoke, real E2E, одинаковом health SHA и
чистом post-deploy log gate. После этого отдельно планируется W8 production
cutover; W9 cleanup не смешивается с первым production release.

## 4. Test pyramid нового Today

| Слой | Что доказывает | Когда запускается |
|---|---|---|
| Unit | canon rules, selectors, state machines, validators, UI branches | каждый packet |
| Contract | Pydantic/OpenAPI/TS/Zod и 16 wire fixtures | W2 onward, CI |
| Integration | PostgreSQL lineage/concurrency, sidecar/API, migrations | W3 onward |
| Replay/parity | production classifier совпадает с frozen W1 | W2/W4 |
| Component | DOM/accessibility на deterministic fixtures | W7 |
| Visual | layout/colors/states без зависимости от LLM text | W7, owner gate |
| Real E2E | Telegram HMAC → API → sidecar → DB → frontend | DEV-RC/W8 |
| Ops/perf | lease, pregen, timeout, cache and release SHA | W5/DEV-RC |
| Release wiring | новый suite действительно вызывается workflow/командой | W7/DEV-RC |

Mock visual tests не заменяют real E2E. Real E2E не использует route
interception. Full replay не заменяет snapshot-linked live validation после
запуска.

## 5. Не делаем до dev RC

- production cutover и W9 destructive cleanup;
- новый message broker/worker pool/WebSocket;
- повторный подбор частот под продуктовую квоту;
- параллельный compatibility envelope;
- хранение counterfactual snapshots;
- массовый LLM pregen всем пользователям;
- отдельную rollback rehearsal для dev RC; неуспешный RC исправляется и
  выкатывается повторно из нового единого SHA;
- полную Chromium/Firefox/WebKit matrix — до dev RC достаточно основного
  Chromium coverage и одного WebKit smoke;
- удаление теста без удаления owning legacy code или равноценной замены в том
  же changeset.
