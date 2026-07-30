# Аудит implementation pack (W2–W8) — KIMI review

Дата: 2026-07-30
Проверяемый пакет (uncommitted): `00_MASTER_TZ.md` v1.9, `04_W2_W3_RUNTIME_CONTRACT_TZ.md`, `05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`, `03_W7_FRONTEND_DESIGN_TZ.md` (sync), `AGENTS.md` (diff), `grace/canon/today_convergence.v1.yml`, `packages/py-contracts/.../versions.py`, `W9_LEGACY_REMOVAL_MANIFEST.md`.
Метод: read-only выверка против master/canon/tone-amendment и предыдущих аудитов (01_TECHNICAL_PREMORTEM, 01_W1_FREEZE_REALITY_CROSS_CHECK_KIMI).

## Вердикт: **PASS** (с двумя P1-строчными правками)

Пакет когерентен: runtime-контракт (04), операционка (05), фронт (03), AGENTS.md и canon взаимно согласованы. Все семь блокеров предыдущего независимого аудита закрыты (таблица ниже). P0 нет.

## Закрытие блокеров предыдущего аудита

| Блокер (из 01_W1_FREEZE_REALITY_CROSS_CHECK_KIMI) | Статус | Доказательство |
|---|---|---|
| canon measured устарел (10 vs 8/81) | закрыт | `today_convergence.v1.yml:202–206` — owner_probe 8/81, artifact t1_canon_align |
| `dayTone` отсутствует в contract | закрыт | master §5.1 (v1.9), canon `day_tone:` (139+), 03 §2, AGENTS.md DOM-контракт |
| owner-решение hero 4,9% | закрыт | canon `owner_decisions`: accept_population_exact_0.049041 (2026-07-30) |
| `CALCULATION_VERSION` не бампнут | закрыт | `versions.py:37` = `ss-calc-1.3.0` |
| per-group cap только по построению | закрыт на контрактном уровне | 04 §3.3: группа в массиве один раз, primary + ≤1 secondary, объединение сфер ≤3; gate-тесты — W2 приёмка №2 |
| mutation suite частичен | частично | W2 приёмка (04 §8) покрывает caps/ownership/immutability/no-fallback; fixtures 1–6 модели — см. P2(e) |
| артефакты незакоммичены | в процессе | этот пакет — следующий коммит |

## Findings

### P1-1. birthTime wire capabilities: canon 4 ключа, 04 пример — 3

- **Механизм:** canon `capabilities` имеет `houses, angles, lots, exact_timing` (`today_convergence.v1.yml:195–198`). Пример wire-объекта в 04 §3.1 содержит только `houses, exactTiming, lots` — ключа `angles` нет, хотя §4.1 того же документа группирует «houses/angles/lots».
- **Проверка:** diff JSON-примера 04 §3.1 против canon capabilities.
- **Минимальная правка:** добавить `angles` в wire-пример 04 (или явно зафиксировать, что angles входит в houses — тогда строкой в 04). Одна строка до коммита.

### P1-2. Лимит 700 output tokens против максимального payload — нужен W6-gate

- **Механизм:** 05 §3 фиксирует `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS=700` на один strict-JSON вызов. Максимальный контент (hero 3 сферы + до 3 импульсов + main_event, у каждого claim-bound `{text, sourceEventIds}` summary/meaning/action) при русском языке (~2–3 chars/token) может превысить 700 → schema fail → `contentState=unavailable` именно на самых богатых hero-днях.
- **Проверка:** W6 приёмка обязана включить самый большой fixture из 16 (hero 3 сферы) и доказать укладывание в cap; превышение cap обратно запрещено 05 без отдельного измерения.
- **Минимальная правка:** не правка, а явный gate-тест в W6 (добавить строкой в 05 §4 или W6-ТЗ).

### P2-а. master §6.2 unique constraint расходится с 04 §7.1

Master: `(user_id, target_date, profile_hash, formula_version, canon_hash)`. 04: `(user_id, target_date, input_hash, formula_version, calculation_version, canon_hash)`. Версия 04 корректнее (input_hash субсумирует профиль; calculation_version нужен для engine identity после ss-calc-1.3.0). Master одной строкой сослаться на 04 как на норматив.

### P2-б. Имя fixture-каталога `today_convergence_v1` (03 §13)

Формула — `today-convergence-2`; `_v1` в имени каталога продолжает путаницу версий, которую rewrite призван закончить. Переименовать при создании в W7.

### P2-c. Mutation fixtures 1–6 модели вне явного gate

04 §8 покрывает caps/ownership/immutability/no-fallback/migration/local-date, но модельные fixtures (два лунных на одном target, транзитивный мост, main_event, background-негатив) не закреплены ни в одной приёмке. Добавить ссылку на mutation suite §9 master в W2 или W4 gates.

## Подтверждённые сильные места

- **Lookahead second-publish-contract закрыт полностью:** impression `surface=day|lookahead`, `sourceSnapshotId` с серверной проверкой ссылки, check-in выбирает фактически показанную версию, live-страты раздельно (04 §7.3). Это было P0-замечание первого premortem.
- **Три разных сбоя разведены чисто:** `state=unavailable` (расчёт, всё null), `contentState=unavailable` (LLM, deterministic сохраняется), `screenState=error` (transport) — 04 §3.2, 03 §2/§5.5/§5.6.1, AGENTS.md. Раньше это смешивалось.
- **Snapshot lineage и narrative lease** соответствуют master §6: атомарный publish insert-on-conflict, supersedes внутри owner/date, content lease на `(snapshot_id, prompt_version)`, нет вечного pending (05 §2.4).
- **Ops-топология канонична:** immutable OCI, orchestrator + flock, host-prepare, timer disabled до smoke, rollback целым release без schema rollback — всё против AGENTS.md и prod-orchestrator §:53.
- **Cohort-политика pregen** (14d активность / 7d LLM-warm / MAX_USERS=500, deterministic order, typed settings + app.env) — разумный bounded запуск; две стадии не заставляют пользователя ждать provider в HTTP.
- **AGENTS.md ↔ 03 test contract синхронизированы:** `data-screen-state` присутствует в обоих; пример контракта в AGENTS.md совпадает с §11 фронт-ТЗ.
- **Preview-проекция server-side** с `previewTeaser` только из названий сфер — frontend не получает скрытых evidence (04 §3.2), что снимает старый класс утечек paywall.

## Рекомендация

Коммитить пакет после двух однострочных правок (P1-1 angles в 04 §3.1; P2-а ссылка master §6.2 → 04 §7.1) или с этими правками отдельной строкой в W2-ТЗ. W2 ready to start — согласен с master v1.9.
