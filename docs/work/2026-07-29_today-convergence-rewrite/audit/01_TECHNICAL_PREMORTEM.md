# Аудит `00_MASTER_TZ.md`: Today Convergence Rewrite

Дата аудита: 2026-07-29  
Проверенный код: `0d4b265a` (`main`, W6-S4a принят)  
Проверенный документ: `docs/work/2026-07-29_today-convergence-rewrite/00_MASTER_TZ.md`  
Метод: technical pre-mortem — предполагаем, что rewrite уже выкатили и он
провалился, затем проверяем причины по реальному репозиторию.

Исходный master-TZ в рамках этого аудита **не изменялся**.

## Вердикт

**REVISE.** Направление rewrite правильное, активная W6 корректно заморожена,
Goodhart-ограничение и отказ от LLM-fallback сформулированы хорошо. Однако
документ пока нельзя декомпозировать в coder-пакеты: в нём остались несколько
взаимоисключающих контрактов, а snapshot/check-in и access boundary не
определены достаточно, чтобы реализация была безопасной и проверяемой.

Ниже перечислены только подтверждённые репозиторием проблемы. Формат каждой:
симптом после релиза → механизм → чем опровергнуть → минимальная правка ТЗ.

## P0 — исправить до начала W1

### 1. Новый публичный контракт теряет access/paywall и не может связать check-in со snapshot

**Симптом после релиза.** Новый endpoint либо раскрывает полный прогноз
`preview/locked`-пользователю, либо frontend не может отличить paywall от
`no_signal`. Даже при правильном расчёте check-in не знает ID прогноза, который
нужно сохранить.

**Механизм и доказательство.** Скетч в master, строки 71–89, содержит state,
convergences и formulaVersion, но не содержит:

- `schemaVersion`, `snapshotId`, `targetDate`, `timezone`, `publishedAt`;
- `access.state/reason`;
- правила публичной проекции для `full | preview | locked`.

Текущий контракт требует `date`, `meta` и `access`
(`apps/api/app/schemas/today.py:514–526`). API вычисляет доступ до TodayService
(`apps/api/app/api/day.py:158–173`), а TodayService отдельно возвращает locked
preview (`apps/api/app/services/today_service.py:228–234`). Это authorization
boundary, а не legacy-деталь, которую разрешено случайно потерять при разрыве
API-контракта.

**Чем опровергнуть.** C1 contract-test с одним и тем же deterministic result для
трёх состояний доступа должен доказать, что locked/preview не получают
запрещённые поля, а payload, который разрешено связать с check-in, содержит
`snapshotId`.

**Минимальная правка ТЗ.** До объявления W0 закрытой зафиксировать полный root
envelope и ортогональность состояний:

```text
calculation state != content state != access state
```

`snapshotId` должен быть nullable только там, где персональный прогноз не был
опубликован. Locked payload не должен создавать видимость опубликованного
персонального прогноза.

### 2. Определение convergence делает `medium` неотличимым от `high`, а `low` нарушает собственный инвариант

**Симптом после релиза.** Все валидные convergence становятся high; ветка
medium либо недостижима, либо зависит от произвольной трактовки кодера. Low
начинает протаскивать фон как дневное схождение.

**Механизм и доказательство.** Master, строка 65, определяет convergence как
`>=2` разных canonical-события и `>=1` сегодняшний якорь. Строка 66 определяет:

- high — `>=2` независимых события + сегодняшний якорь;
- medium — один якорь + связанный поддерживающий фактор;
- low — только фон или слабый одиночный сигнал.

High буквально повторяет eligibility convergence. Medium тоже описывает два
фактора с якорем, но не объясняет отличие от high. Low противоречит правилу
«фон сам не создаёт convergence» и состоянию `single_impulse`. Кроме того,
`no_signal` указан как polarity группы, хотя это root state, а не полярность.

**Чем опровергнуть.** Таблица минимум из 12 ручных примеров должна давать ровно
один ожидаемый `state`, `polarity` и `evidence_level` без дополнительных
решений исполнителя. Mutation «убрать второй независимый event» обязана
переводить convergence в impulse/no_signal, а не в low-convergence.

**Минимальная правка ТЗ.** До W1 дать отдельные формальные таблицы:

1. eligibility группы;
2. агрегация polarity (`supportive | tense | mixed` — без `no_signal`);
3. evidence-level только среди уже валидных групп;
4. presentation threshold.

Также закрыть поведение нескольких несвязанных импульсов: публично выбирается
ровно один по указанному ranking либо контракт содержит `impulses[]`. Сейчас D2
говорит об одном импульсе, но tie-break отсутствует.

### 3. Матрица `state x contentState` противоречит «переиспользуемому» валидатору и не решает 75-секундный cold path

**Симптом после релиза.** `no_signal` ошибочно маркируется как LLM-ready либо
как LLM-failure; cache отвергает валидные детерминированные дни. При provider
timeout повторные GET снова запускают платную генерацию и продолжают ждать.

**Механизм и доказательство.** Master, строки 27–29, оставляет в силе старую
матрицу и honest cache, но новый скетч, строка 87, допускает только
`ready | unavailable`. Принятый валидатор содержит четыре значения
`ready | pending | unavailable | not_needed` и отдельную матрицу старых state
(`apps/api/app/schemas/today_focus.py:134–170`). Эти state переименованы в
rewrite, поэтому валидатор нельзя «переиспользовать» без новой таблицы.

Текущий hard deadline фактически равен 25 секундам, а sidecar/DB находятся вне
него (`apps/api/app/services/today_service.py:149–153`). Honest cache отклоняет
`pending/unavailable` как hit (`today_service.py:1132–1149`). Cache write —
select-then-insert/update без generation lease (`today_service.py:1175–1211`).
Такой механизм под конкурентными cache misses не доказывает ни latency, ни
single-flight.

**Чем опровергнуть.** Нагрузочный contract-test: 20 одновременных GET одного
`user/date` при зависшем LLM. Проверить верхнюю границу latency, количество
provider calls, отсутствие duplicate-row ошибки и то, что факты возвращаются.

**Минимальная правка ТЗ.** Зафиксировать новую матрицу, например:

```text
convergence/single_impulse -> pending | ready | unavailable
no_signal                  -> not_needed
calculation unavailable    -> contentState=unavailable
```

Точные значения — решение C1, но `not_needed` и реальный async `pending` нельзя
молча удалить. Отдельно задать SLO cache-hit/cold deterministic path и один
generation lease/cooldown на `(snapshot_id, prompt_version)`. `unavailable` не
считается успешным прогревом, но factual snapshot может быть отдан сразу, не
запуская новый provider-call на каждый refresh.

### 4. Snapshot не имеет identity/concurrency/ownership-контракта

**Симптом после релиза.** Два параллельных запроса публикуют два разных
«замороженных» дня; пользователь может прислать чужой snapshot ID в check-in;
редактирование check-in незаметно меняет связь с прогнозом. `published_at`
ошибочно принимается за доказательство, что прогноз был виден на экране.

**Механизм и доказательство.** В master, строки 98–112, перечислены поля, но нет:

- unique/index rules и атомарной операции publish;
- правила выбора snapshot при нескольких formula/canon/input identity;
- проверки `snapshot.user_id == authenticated user` и совпадения target_date;
- `ON DELETE`/retention policy;
- различия между «API отдал» (`published_at`) и «UI показал»
  (`prediction_seen_at`).

При этом `prediction_seen_at` нельзя честно записать в EveningCheckin в момент
показа: строки check-in ещё нет, а её обязательный mood появляется только
вечером. Нужен минимальный impression record у snapshot (или отдельное
событие), из которого timestamp переносится/связывается при submit check-in.

Текущий check-in является upsert по `(user_id, target_date)`
(`apps/api/app/db/models.py:603–621`,
`apps/api/app/services/checkin_service.py:140–173`). Endpoint передаёт только
поля формы (`apps/api/app/api/checkin.py:67–96`). Поэтому nullable FK сам по
себе не создаёт корректную lineage.

**Чем опровергнуть.** Обязательные DB/API-тесты: concurrent publish; повторный
GET; cross-user snapshot injection; snapshot с другой датой; повторное
редактирование check-in; удаление пользователя; supersedes другой даты/owner.

**Минимальная правка ТЗ.** В W3 заранее определить:

- immutable snapshot identity и unique constraint;
- атомарный publish/claim;
- same-owner + same-date FK validation;
- `supersedes_snapshot_id` только внутри owner/date и без циклов;
- server-side impression endpoint/event для `prediction_seen_at`;
- правило: редактирование check-in сохраняет исходную связь, если пользователь
  явно не видел более новый опубликованный snapshot.

`snapshotId` обязан входить в C1 payload из замечания 1.

### 5. Обещанная проверка polarity и времени не измеряется текущим check-in

**Симптом после 60–90 дней.** Дашборд показывает «engine agreement», но данные
не позволяют установить, какая polarity относилась к какой сфере и в какое
время что-то произошло.

**Механизм и доказательство.** Теги действительно существуют
(`lib/contracts/checkin.ts:19–39`, `apps/api/app/db/models.py:631–639`), но они
не являются парой `(sphere, polarity)`. Например, `argument` и `support`
неоднозначны между work/relationships/communication; при нескольких
`observed_spheres[]` невозможно понять соответствие тегов сферам. Время
проявления форма вообще не собирает. Поэтому метрика master, строка 232,
«сфера, polarity, время» не следует из данных строк 116–120.

Кроме EveningCheckin есть отдельный Telegram feedback path — таблица
`day_feedback` (`apps/api/app/db/models.py:856–883`) и callback endpoint. Он
сохраняет accuracy без snapshot linkage
(`apps/api/app/api/telegram_webhook.py:121–137`). Blast radius master его не
упоминает.

**Чем опровергнуть.** Написать SQL на существующей/планируемой схеме, который
для check-in с двумя выбранными сферами однозначно возвращает observed
polarity и observed time для каждой из них. Сейчас такой SQL невозможен.

**Минимальная правка ТЗ.** Не возвращать тяжёлую матрицу 12 сфер. Для MVP
честно ограничить метрики:

- selected-sphere hit/coverage;
- общая accuracy/copy resonance;
- polarity — только weak label для однозначных комбинаций, не ground truth;
- time agreement — `not measured` до отдельного поля/исследования.

Либо добавить snapshot linkage в DayFeedback, либо явно исключить Telegram
feedback из engine-validation. Напоминание «насколько попал прогноз» нельзя
отправлять человеку, которому этот прогноз не был показан.

### 6. Lookahead на завтра создаёт второй скрытый publish-контракт

**Симптом после релиза.** Сегодня пользователь видит прогноз на завтра, ночью
formula/canon или входные данные меняются, а завтра check-in связывается уже с
другой версией. Валидация считает «попадание» не для той prediction, которую
человек видел.

**Механизм и доказательство.** D1, строка 52, встраивает tomorrow lookahead в
сегодняшний `no_signal`. Pregen действительно считает tomorrow
(`apps/api/app/jobs/day_pregen.py:99–124`, default `--days-ahead=1`), но он
только пишет Today cache: publication/impression следующего дня не фиксируется.

**Чем опровергнуть.** Сценарий: pregen завтра → показать lookahead сегодня →
сменить canon → открыть завтра → отправить check-in. Должен существовать один
однозначный snapshot, который был увиден и против которого идёт оценка.

**Минимальная правка ТЗ.** Самый дешёвый вариант без оверинжиниринга —
убрать lookahead из первой версии rewrite и оставить в `no_signal` только
детерминированный `period_context`. Если lookahead принципиален, он обязан
нести `lookaheadSnapshotId`, публиковать/замораживать tomorrow snapshot и
записывать impression; это отдельный срез, а не «pregen и так считает».

### 7. «Динамические 0–3 сферы» снова превращаются в обязательные 12 через disclosure

**Симптом после релиза.** Первый экран новый, но ниже остаётся прежняя модель:
12 ежедневных оценок, среди которых отсутствие сигнала визуально выглядит как
neutral. Пользователь снова получает «в каждой сфере что-то происходит».

**Механизм и доказательство.** Master одновременно говорит о выборе 0–3 сфер
(строка 67) и сохраняет полный список 12 в disclosure/endpoint
(строки 38, 52, 93, 223). Текущий UI действительно рендерит полный
`ConcreteDayAdvice` перед focus (`components/today/today-screen.tsx:269–280`).
Если W7 просто перенесёт его в disclosure, старая valence-модель останется
публичной несмотря на заявленный supersession.

**Чем опровергнуть.** DOM/e2e для `no_signal` и одной convergence: в публичном
дереве нет 12 строк с дневным статусом/polarity; невыбранная сфера нигде не
маркируется neutral.

**Минимальная правка ТЗ.** Зафиксировать одно из двух:

1. полный список — только статическая навигация без daily verdict/copy; либо
2. в rewrite v1 его вообще нет.

С учётом принятого продуктового решения и минимизации scope рекомендуется
вариант 2. Наличие отдельной страницы сфер можно решить позже.

## P1 — обязательные уточнения до соответствующей волны

### 8. Текущий `factor_id` не является стабильным canonical event ID

**Симптом после релиза.** Один физический факт получает другой public event ID
в зависимости от того, пришла ли activation layer. Snapshot lineage и mutation
tests фиксируют ложное изменение события.

**Механизм и доказательство.** Ledger действительно дедуплицирует по
`semantic_key`, но ID победителя различается:

- activation: `act:<activation_id>`
  (`apps/api/app/services/day_factor_ledger.py:188–203`);
- signal: `sig:aspect:...` (`day_factor_ledger.py:228–253`).

`TodayFactor` не сохраняет `semantic_key`
(`apps/api/app/services/today_focus_builder.py:105–127`), а public ID строится
как `ev:<factor_id>` (`today_focus_builder.py:593–605`). Поэтому утверждение
master, строки 25 и 62, что текущие canonical events можно переиспользовать как
единый ID во всех слоях, пока не доказано.

**Чем опровергнуть.** Один и тот же физический aspect прогнать с activation
layer и без неё; canonical event ID обязан остаться byte-identical, меняется
только provenance/data quality.

**Минимальная правка ТЗ.** Переиспользовать принцип ledger/timing/provenance,
но не объявлять текущий public ID каноническим. В W1 определить versioned
identity из нормализованных физических полей и event window. Producer
precedence обогащает поля и provenance, но не меняет identity.

### 9. `canonical_input (или ссылка)` недоопределён, а `type=replay` противоречит решению не хранить контрфактики в prod

**Симптом после релиза.** Либо replay через 90 дней невозможен, потому что
сохранён только hash, либо БД ежедневно дублирует raw natal/profile payload и
чувствительные данные. Отдельные replay rows начинают смешиваться с тем, что
реально видел пользователь.

**Механизм и доказательство.** Master, строки 100–112, оставляет два разных
варианта хранения без выбора и одновременно вводит отдельный `type=replay`.
Текущий репозиторий уже хранит natal context отдельно и привязывает Today cache
через profile hash (`apps/api/app/db/models.py:355–388`,
`apps/api/app/services/natal_context_service.py:250–273`). Санитизированные
focus fixtures прямо запрещают raw profile/natal payload
(`apps/api/tests/fixtures/today_focus/README.md`).

**Чем опровергнуть.** На копии published snapshot удалить текущие canon-файлы,
изменить профиль и воспроизвести byte-identical deterministic result только из
сохранённой lineage. Одновременно privacy scanner не должен находить birth
coordinates/time/Telegram identity в snapshot audit.

**Минимальная правка ТЗ.** Выбрать один механизм:

- prod snapshot table хранит только `published`;
- `canonical_input_ref` указывает на immutable content-addressed normalized
  factor pack, без raw Telegram/profile полей;
- hash serialization, SHA-256, engine/ephemeris/sidecar/formula/canon versions
  заданы каноном;
- replay output — offline artifact или временный job-result с TTL, не
  пользовательский snapshot и не `type=replay` в основной таблице.

### 10. Pipeline может честно исключать unmapped уже после того, как normalization выдумала house 1

**Симптом после релиза.** Невалидные house cusps превращаются в первый дом и
дают уверенную, но ложную сферу. Audit показывает mapped factor, поэтому
`excluded_unmapped` не ловит ошибку.

**Механизм и доказательство.** API normalization при ошибке `find_house`
использует `or 1` и для транзитов, и для натала
(`apps/api/app/services/normalization_service.py:150–162` и `207–224`). Это
противоречит fail-closed направлению rewrite. Известный долг отдельно отмечен
в AGENTS.md: sidecar не отдаёт `planet.house`, API повторно вычисляет mapping.

**Чем опровергнуть.** Mutation с отсутствующими/невалидными cusps: не должно
появиться ни одного house-1 factor; должен увеличиться invalid/excluded counter.

**Минимальная правка ТЗ.** В W1/W2 определить raw boundary: `planet.house`
приходит от sidecar либо равен null; `or 1` запрещён; null исключается с reason
code. Если sidecar-контракт меняется, sidecar входит в атомарный deploy и
contract tests.

### 11. Blast radius не определяет поведение Calendar/Yesterday/Readings/event drilldown после удаления dayStatus

**Симптом после релиза.** Today работает, а Calendar продолжает вычислять
старый dayStatus; readings получают несовместимый payload; event drilldown
выбирает неоднозначный cache/snapshot; `/day/today` расходится с локальной
датой пользователя около полуночи.

**Механизм и доказательство.** Master перечисляет потребителей, но не даёт
таблицу replacement contract. Реальные зависимости:

- Calendar отдельно читает/вычисляет old status
  (`apps/api/app/services/calendar_service.py:184–266`);
- frontend/readings берёт `payload.dayStatus`
  (`lib/api/readings.ts:70–82`);
- focus-event drilldown ищет cache только по user/date и вызывает
  `scalar_one_or_none` (`apps/api/app/api/day.py:211–238`), хотя versioned cache
  и будущая lineage допускают несколько строк;
- `/api/day/today` сейчас разрешает `today` через UTC, не timezone профиля
  (`apps/api/app/api/day.py:133–139`).

**Чем опровергнуть.** Real contract suite вокруг полуночи и DST, содержащий
Today, Calendar, Yesterday, Readings и focus-event drilldown на одном
snapshot/formula version.

**Минимальная правка ТЗ.** До W5 добавить consumer matrix:

```text
consumer -> какие поля получает -> какой snapshot -> access rule -> cache key
```

Calendar должен получать компактный convergence summary, а не заново запускать
старую valence. Yesterday/check-in не должны задним числом генерировать
«прогноз, который якобы был показан». Drilldown адресуется через snapshot/event
identity. Исправление local `today` — обязательный TZ/DST gate.

Отдельно: D3 вводит push/opt-in, но в репозитории нет daily push preference или
day-notification pipeline. Это самостоятельная продуктовая фича. Чтобы не
раздувать rewrite, оставить рассчитанный evidence в API, а push вынести в
отдельный master после cutover.

### 12. Destructive cleanup gate через `rg` не защищает данные и не доказывает rollback

**Симптом после релиза.** W9 удаляет не только derived Today rows либо rollback
старого OCI образа запускается на уже несовместимой схеме.

**Механизм и доказательство.** Master, строка 192, использует текстовый `rg` как
legacy-removal gate. Он полезен для кода, но ничего не проверяет в DB. В той же
БД живут access, payments, subscriptions, check-ins и Telegram feedback;
app rollback по канону не откатывает schema.

**Чем опровергнуть.** Staging rehearsal: old app + additive schema → new app +
schema → rollback old app; сравнить protected-table row counts и FK integrity.
Затем dry-run destructive migration выводит точный allowlist удаляемых Today
таблиц/колонок.

**Минимальная правка ТЗ.** Для W8/W9 добавить:

- protected data denylist: users, profiles, access ledger, payments,
  subscriptions, EveningCheckin, DayFeedback и остальные paid reports;
- явный allowlist только derived Today/cache/semantic/history данных;
- migration compatibility test старого app с новой additive schema;
- pre-cleanup dump + restore rehearsal;
- sidecar digest в атомарный release, если выполняется замечание 10.

## P2 — качество результата, не блокирует W1-schema

### 13. Текущий и предложенный LLM-валидатор проверяет форму, но не доказательность жизненного события

**Симптом после релиза.** Текст выглядит очень конкретным, но выдумывает
разговор, спор или сообщение. Пользователь воспринимает это как предсказанное
реальное событие, хотя расчёт содержит только астрологический факт.

**Механизм и доказательство.** Few-shot master, строки 138–152, утверждает
«разговор ... зайдёт в тупик», «спор ... перерастает», «сообщение ... покажется
резче». Это не вычисленные события. Текущий focus validator проверяет ключи,
длины, кириллицу и jargon, но не связь смысловых claims с evidence
(`apps/api/app/services/llm_claim_validator.py:84–169`). Простое требование
упомянуть один факт не запрещает добавить рядом неподтверждённый сценарий.

**Чем опровергнуть.** Adversarial fixture: корректные event IDs + полностью
выдуманный жизненный сценарий. Validator обязан отвергнуть весь atomic response.

**Минимальная правка ТЗ.** Различать:

- рассчитанное событие: аспект/фаза/время/окно;
- возможное проявление: только модальная формулировка «может проявиться как»;
- фактическое жизненное событие: известно только после check-in.

LLM output должен возвращать source event IDs на каждый claim. Время и окно
подставляются детерминированно, а не генерируются. Few-shot следует сделать
конкретным, но не категоричным.

## Что в master уже хорошо и не является оверинжинирингом

- Полный supersession старой волны и явный последний SHA.
- Отказ от квотной калибровки формулы; распределения — мониторинг, не gate.
- 0–3 выбранные сферы и запрет фонового convergence.
- `formula_version`, immutable published snapshot, audit и lineage.
- Snapshot-linked check-in при условии замечаний 1, 4 и 5.
- Mutation suite и постоянный replay-harness.
- Additive migration и отдельный destructive release.
- Запрет текстового fallback при сохранении вычисленных фактов.

## Что действительно следует урезать

Чтобы rewrite не разросся, из первой версии рекомендуется убрать:

1. tomorrow lookahead — до появления cross-date snapshot/impression контракта;
2. full 12-sphere daily disclosure — оставить только выбранные 0–3;
3. daily tense/supportive push и opt-in UI — отдельная фича после cutover;
4. persistent counterfactual/replay rows в production;
5. попытку валидировать per-sphere polarity/time без данных, которых check-in не
   собирает.

Это не снижает точность движка. Наоборот, оставляет один проверяемый продуктовый
контракт: **что действительно сошлось сегодня, в какой сфере, с какой
полярностью и на каких независимых вычисленных событиях**.

## Минимальный amendment checklist перед PASS

- [ ] Полный C1 root envelope: schema/snapshot/date/timezone/access/formula.
- [ ] Формальные truth tables: state, group eligibility, polarity,
      evidence_level, presentation.
- [ ] Новая `state x contentState` матрица + cold/cache SLO + single-flight.
- [ ] Snapshot identity, publish, impression, ownership/date validation и DB
      constraints.
- [ ] Честный scope check-in metrics; решение по Telegram DayFeedback.
- [ ] Lookahead/12-sphere/push вынесены либо получили отдельные контракты.
- [ ] Стабильный canonical event ID доказан mutation-тестом producer parity.
- [ ] Выбран один privacy-safe canonical input/ref и удалён prod `type=replay`.
- [ ] Fail-closed house mapping вместо `or 1`.
- [ ] Consumer matrix + local-day/DST + event drilldown identity.
- [ ] Protected-data allowlist/denylist и rollback rehearsal.

После внесения этих поправок в master вердикт можно повторно пересмотреть на
**PASS** и только затем нарезать W1 на coder-пакеты.
