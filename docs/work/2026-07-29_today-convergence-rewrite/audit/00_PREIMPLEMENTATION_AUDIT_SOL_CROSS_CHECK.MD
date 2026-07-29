# Cross-check аудита `00_PREIMPLEMENTATION_AUDIT.md`

Дата: 2026-07-29  
Проверенный код: `0d4b265a` (`main`, W6-S4a)  
Проверенные документы:

- `audit/00_PREIMPLEMENTATION_AUDIT.md` — аудит coding-leader;
- `00_MASTER_TZ.md` — нормативный план rewrite;
- фактический код `/opt/solarsage-astro`.

Этот файл — отдельное мнение и cross-check. Исходный аудит, master-TZ и
`01_TECHNICAL_PREMORTEM.md` не изменялись.

## Итоговое мнение

Аудит coding-leader полезен и в основном фактологически точен. Его сильная
сторона — инвентаризация существующего кода: GAP/DRIFT действительно показывают,
что старую модель нельзя «слегка подкрутить».

Но его итоговая классификация слишком мягкая: несколько пунктов отмечены `OK`,
хотя это только заготовки, несовместимые с новым контрактом. Поэтому использовать
его нужно так:

- GAP/DRIFT — как подтверждённый список работ;
- RISK — как обязательные вопросы W1/W3/W7;
- OK — только как «есть код, который можно изучить», не как разрешение
  переиспользовать без mutation/contract test.

Мой итоговый verdict остаётся **REVISE**.

## Что из аудита принимаю без оговорок

### GAP-1/2/3 — snapshot, check-in и formula version

Это P0. В текущем коде нет immutable `day_snapshots`, связи
`EveningCheckin → forecast_snapshot`, `published_at`/lineage и явного
`formula_version`. `TodayPayloadCache` — технический cache, не published
прогноз (`apps/api/app/db/models.py:355–388`), а check-in сейчас upsert'ится
только по `(user_id, target_date)` (`models.py:603–621`).

Добавить нужно не только nullable FK, но и правила:

- snapshot принадлежит тому же user и target_date;
- publish атомарен и immutable;
- `supersedes_snapshot_id` не образует циклы;
- публичный payload отдаёт `snapshotId`;
- `published_at` (API отдал) не смешивается с `prediction_seen_at` (UI показал).

Последний пункт важен: в момент показа EveningCheckin ещё может не существовать,
поэтому `prediction_seen_at` должен жить в impression record/event у snapshot и
связываться с check-in позже, либо иметь явно оговорённую серверную семантику.

### GAP-4/5 — replay и mutation suite

Принимаю полностью. Это не научный overkill, а минимальная самопроверка:

- replay отделяет честную формулу от ручной подгонки распределения;
- mutation доказывает dedup, независимость, TZ/DST и immutable publish.

Replay должен работать из сохранённого privacy-safe canonical input/ref, а не из
одного hash и не из raw Telegram/profile payload.

### GAP-6 — theme registry

Принимаю. Сейчас `theme_keys` приходят из activation layer, а отдельного
канонического registry нет (`today_focus_builder.py:720–753`). Узкая тема должна
быть версионированным источником truth, иначе правило «общая тема» снова станет
неявной магией.

### DRIFT-1…DRIFT-5

Все пять drift подтверждаются кодом и должны перейти в rewrite:

- неизвестное отображение не должно становиться `work`
  (`today_focus_builder.py:251–271`);
- convergence должна быть per-sphere, а не `family_count` на target;
- нельзя оставлять одну `winning_group`
  (`today_focus_builder.py:813–835`);
- global dayStatus не должен быть продуктовой истиной;
- старый `confidence` нельзя просто переименовать — нужна новая семантика
  `evidence_level` по независимым событиям и сегодняшнему якорю.

### RISK-1, RISK-6, RISK-7 и список дополнительных consumers

Единый mapping technical → product sphere обязателен: сейчас есть как минимум
словарь в `today_focus_builder.py`, так и mapping из `day_valence.v1.yml`
(`day_valence_service.py:42–70`).

Также нужно мигрировать не только Today: Calendar, DaySummary, DayChart,
WeekStrip, `lib/contracts/today.ts`, check-in hint и readings. Отдельный
`DayFeedback` Telegram path тоже должен получить решение по snapshot linkage;
аудит coding-leader его не включил в blast radius.

## Что принимаю, но только с оговоркой

### OK-1/OK-2 — canonical events и public event selection

Переиспользовать можно алгоритмические идеи (timing, provenance, cap, sorting),
но не объявлять текущий ID уже каноническим. Сейчас:

- activation получает `act:<id>`;
- signal получает `sig:aspect:...`;
- `TodayFactor` теряет `semantic_key`;
- public ID строится из `factor_id`.

Один и тот же physical event с activation layer и без неё может получить разные
ID. Нужен producer-parity mutation test до статуса `OK`.

### OK-3 — bounded LLM phase

Инфраструктурная заготовка хорошая (`asyncio.wait`, cancel+await,
`CancelledError`), но это не закрывает UX-проблему 75 секунд. В коде hard phase
budget по умолчанию 25 секунд (`today_service.py:149–153`), а provider timeout
`min(60, remaining)` — только timeout отдельной попытки. Нельзя трактовать это
как «hard deadline = 60».

В master надо отдельно зафиксировать cold-path SLO, cache-hit SLO и поведение при
provider failure. Иначе `unavailable → cache miss` может запустить новый LLM на
каждый refresh (`today_service.py:1132–1149`). Нужны generation lease и
retry/cooldown, а не только miss predicate.

### OK-4/OK-5 — schema matrix и honest cache

Основа есть, но старый validator нельзя перенести буквально: он знает
`convergence_today/single_impulses/background_only/no_accent` и
`ready/pending/unavailable/not_needed`
(`apps/api/app/schemas/today_focus.py:134–170`). Новый master вводит другие
root states и в публичном скетче оставляет только `ready | unavailable`.

До W1 нужна новая truth table. Особенно важно отделить:

```text
calculation state != content state != access state
```

Для `no_signal` обычно нужен `contentState=not_needed`, а для retryable LLM
может потребоваться `pending`.

### OK-6 — no-fallback

Для нового focus-блока fail-closed действительно уже есть. Но старый
TodayService всё ещё подставляет fallback-тексты в headline/reading/notes/why
(`today_service.py:678–690`). Если rewrite действительно удаляет V1/V2 public
paths, эти поля нельзя оставить незаметно в новом envelope под видом
«совместимости».

### OK-8 — LLMClaimValidator

Базовая инфраструктура пригодится, но текущий validator проверяет форму, длину,
jargon и совпадение ключей (`llm_claim_validator.py:84–169`), а не доказанность
смыслового claim. Корректные event IDs плюс выдуманный жизненный сценарий сейчас
могут пройти. Нужен adversarial test и source-event ID для каждого claim;
время подставляется детерминированно, не генерируется LLM.

## Что в аудите нужно исправить или считать устаревшим

### 1. `W0 — закрыта` — преждевременно

В сводке аудита W0 названа закрытой. Это неверно как pre-implementation verdict:
не закрыты access envelope, state/evidence truth table, snapshot publication,
check-in impression, lookahead и 12-sphere policy. До их фиксации W0 должна быть
`REVISE`, а не `OK`.

### 2. «Строить новый pipeline параллельно» — только в изолированном коде

Рекомендация аудита строить новый pipeline параллельно полезна как стратегия
разработки и replay. Но нельзя запускать два публичных runtime-пути или dual-run,
который влияет на пользовательский результат/cache identity. Разрешённый
вариант: новый pure module + fixtures + replay, затем один атомарный cutover.

### 3. RISK-4 сформулирован неточно

`25s` — hard phase budget, `60s` — верхняя граница provider attempt. Это разные
величины. Не нужно молча менять фазу на 60 секунд; нужно задать продуктовый SLO
и решить, будет ли copy асинхронным при cold miss.

### 4. `W5 = OK` для pregen — только базовый вызов

То, что job вызывает TodayService (`day_pregen.py:113`), верно. Но typed outcomes,
retry, coverage exit code, current+tomorrow policy и безопасные логи ещё должны
быть отдельным acceptance gate. Сейчас job печатает raw `user.id`
(`day_pregen.py:121,124`), что нельзя переносить в telemetry.

## Дополнительные P0/P1, которых не хватило в исходном аудите

### Access/paywall потерян в публичном скетче

Текущий root payload обязан содержать `access`, `meta` и `date`
(`apps/api/app/schemas/today.py:514–526`), а endpoint рассчитывает доступ до
генерации (`apps/api/app/api/day.py:158–173`). Новый контракт должен явно
описать `full | preview | locked`; иначе rewrite может раскрыть premium facts.

### Lookahead создаёт cross-date publication

D1 показывает tomorrow forecast внутри сегодняшнего `no_signal`, но pregen лишь
пишет cache (`day_pregen.py:99–124`) и не фиксирует, что tomorrow prediction была
показана. Для v1 lookahead лучше убрать. Иначе нужен отдельный
`lookaheadSnapshotId` и impression lineage.

### 12 сфер возвращаются через disclosure

Master одновременно требует 0–3 выбранные сферы и полный 12-sphere disclosure.
Текущий UI рендерит старый полный `ConcreteDayAdvice`
(`components/today/today-screen.tsx:269–280`). Это может вернуть старую ложную
нейтральность. Для rewrite v1 лучше оставить только выбранные 0–3, а статическую
навигацию сфер решать отдельно.

### Локальная дата и fail-closed house mapping

`/api/day/today` сейчас разрешает `today` через UTC
(`apps/api/app/api/day.py:133–139`), а normalization превращает не найденный дом
в `1` (`apps/api/app/services/normalization_service.py:150–162, 207–224`). Оба
случая должны быть отдельными TZ/mutation gates; неизвестный house исключается,
а не становится первой сферой.

### Snapshot/check-in metrics недостаточно для polarity/time agreement

Теги сохраняются, но generic `argument/support/tired` не дают однозначной пары
`(sphere, polarity)`, а время проявления не собирается. Поэтому первые метрики
должны быть sphere coverage и copy resonance; polarity/time — weak label или
`not measured`. Telegram `DayFeedback` надо либо связать со snapshot, либо
исключить из engine agreement.

### Rollback и destructive cleanup

`rg`-gate полезен для поиска старых символов, но не защищает DB. До W9 нужен
allowlist derived Today-таблиц и denylist users/profiles/access/payments/
subscriptions/check-ins/paid reports, плюс staging rollback rehearsal.

## Приоритет принятия

До выдачи W1 coder-пакета закрыть в таком порядке:

1. C1 root envelope: access, snapshotId, date/timezone, schema/formula versions.
2. Truth tables: state, group eligibility, polarity, evidence, contentState.
3. Snapshot publish/impression/ownership и check-in/DayFeedback semantics.
4. Убрать/отложить lookahead, 12-sphere daily disclosure и push.
5. Стабильный event identity, единый mapping/theme registry, fail-closed houses.
6. Cold/cache SLO, single-flight/retry и consumer matrix для Calendar/Readings/
   Yesterday/drilldown.

После этого исходный audit можно использовать как implementation inventory,
а этот cross-check — как acceptance gate. До выполнения пунктов verdict:
**REVISE, кодеру не выдавать новую волну**.
