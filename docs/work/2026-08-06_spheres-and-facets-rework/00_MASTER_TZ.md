# MASTER ТЗ: пересборка 12 продуктовых сфер и проявлений внутри сфер

Дата: 2026-08-06  
Статус: REVISED после проверки против repository main + UX-решения владельца по прототипу (`01_UX_DECISIONS_FROM_PROTOTYPE.md`, обязателен совместно); готово к реализации  
Область: Today Convergence, страницы сфер (decommission), narrative, check-in, frontend и generated contracts

## 1. Контекст и принятые решения

Текущая версия Today Convergence ещё не выкачена в production. Поэтому изменение выполняется как **прямая переделка текущей реализации**, без compatibility-слоя и параллельных версий поведения.

Обязательные правила:

- не создавать `v2`-реализацию рядом с текущей, адаптеры совместимости, dual-read/dual-write, shadow и feature flag;
- не сохранять старые product keys «на всякий случай»;
- изменить каноны, runtime, Pydantic/OpenAPI/generated TypeScript, frontend, fixtures и тесты атомарно;
- старое поведение остаётся только в git history;
- rollback — git revert всего пакета;
- физическая формула convergence не меняется: significance, eligibility, direct-star grouping, independence, hero C1, tone и birth-time rules остаются прежними.

Отдельный файл `product_spheres.v1.yml` **разрешён и обязателен**. Это не новая версия старого канона, а отсутствующий канон другой сущности — продуктовых сфер. Технический scoring-канон `spheres.v1.yml` не переписывать.

---

## 2. Проблема

### 2.1. Текущие 12 карточек не образуют единую систему

На одном уровне смешаны:

- жизненные области: работа, деньги, отношения, здоровье;
- действия: решения, покупки;
- виды активности: спорт, учёба, поездки, общение.

При этом отсутствуют самостоятельные области «Дом и семья» и «Друзья и планы».

`decisions` не является сферой: решение всегда относится к работе, финансам, отношениям и т. п.  
`shopping` не является сферой: покупка — одно из финансовых проявлений.

### 2.2. Fan-out раздувает один физический факт

В `grace/canon/today_convergence.v1.yml` продуктовая проекция строится одновременно через:

- `technical_to_product`;
- `technical_alias_to_product`;
- `planet_to_product`;
- `planet_sphere_limits`.

Из-за этого один physical unit получает несколько продуктовых сфер, а широкая смесь фактов попадает в group projection и LLM. Следствия:

- документы смешиваются с деньгами;
- здоровье получает общий 8/12-домный фон;
- поездки появляются из одного Урана;
- творчество появляется из Нептуна/Урана без 5-го дома;
- narrative дописывает конкретный жизненный сюжет, которого нет в fact-pack.

### 2.3. Полярность ошибочно обобщается на всю сферу

В один день возможны независимые сигналы:

```text
finance / personal_money / supportive
finance / financial_obligations / tense
```

Это не означает, что «все финансы смешанные». Это означает:

- личные деньги — поддержка;
- обязательства — напряжение.

Полярность должна принадлежать отдельной физической группе/сигналу. Тайлу разрешена только краткая агрегированная сводка.

### 2.4. Diversity-gate теряет второй сигнал той же сферы

Текущий selector отбрасывает следующую группу, если она не добавляет новую sphere. Поэтому две независимые финансовые группы способны съесть друг друга.

Сначала выбираются физические сигналы по существующему ranking, затем они раскладываются по sphere/facet. Повтор sphere не является причиной исключения.

### 2.5. Продуктовая и техническая таксономии сейчас не разделены

`grace/canon/spheres.v1.yml` — технический scoring-канон из девяти кластеров с домами, планетами, лотами и весами. Его используют scoring, semantic, day ledger, valence и страницы сфер. Он не является реестром 12 product spheres и не должен им становиться.

---

## 3. Целевой список 12 product spheres

Фиксированный порядок и ключи:

1. `work` — Работа
2. `finance` — Финансы
3. `documents` — Документы
4. `relationships` — Отношения
5. `sport` — Спорт
6. `communication` — Общение
7. `health` — Здоровье
8. `home_family` — Дом и семья
9. `travel` — Поездки
10. `creativity` — Творчество
11. `study` — Учёба
12. `friends_goals` — Друзья и планы

Явный breaking rename:

```text
money → finance
```

Полностью удалить product keys:

```text
decisions
shopping
```

Отдельных routes для этих ключей нет: dynamic route сохраняется, а доступность определяется новым union/каноном. Не создавать redirects.

---

## 4. Facets — конкретные проявления sphere

`facet` — обычное nullable-поле существующего сигнала, а не отдельная карточка, сервис или ontology engine.

Каждый опубликованный physical signal получает:

```text
sphere: ровно одна product sphere
facet: один facet этой sphere либо null
polarity: polarity этой physical group/unit
```

Secondary sphere и secondary facet удалить. Один физический сюжет не клонируется.

### 4.1. Работа

- `daily_work` — текущие задачи, служебная нагрузка, рутина; дом 6;
- `career_status` — карьера, статус, продвижение, публичная роль; дом 10.

### 4.2. Финансы

- `personal_money` — доход, расходы, накопления, личное имущество; дом 2;
- `shared_money` — общий бюджет, средства партнёра, страхование, наследование; дом 8;
- `purchases_transactions` — покупка, продажа, цена, сделка; дом 2 + явный transaction-context;
- `financial_obligations` — кредит, долг, налог, рассрочка, возврат; дом 8 + явный obligation-context.

Меркурий, Венера и Сатурн могут уточнять, но не создают узкий facet самостоятельно.

### 4.3. Документы

- `admin_documents` — заявления, справки, переписка, обычное оформление; дом 3;
- `legal_foreign_education_documents` — юридические, иностранные, визовые, образовательные документы; дом 9;
- `contracts` — договор между сторонами; дом 7 + contract-context;
- `financial_documents` — счета, кредитные, налоговые, страховые документы; дом 2/8 + finance-context;
- `property_documents` — документы на жильё/недвижимость; дом 4 + property-context.

Не собирать один сигнал «Документы» сразу из всех перечисленных домов.

### 4.4. Отношения

- `romance` — симпатия, свидания, романтика; дом 5;
- `partnership` — пара, брак, взаимодействие один на один; дом 7.

Семья и домашний быт относятся к `home_family`, если нет самостоятельной relationship-темы.

### 4.5. Спорт

- `physical_energy` — телесная активность и готовность действовать; дом 1;
- `training_routine` — режим и повторяющаяся тренировка; дом 6;
- `competition_performance` — соревнование/выступление; дом 5/10 + sport-context.

Один Марс не создаёт sport facet.

### 4.6. Общение

- `everyday_contacts` — разговоры, переписка, повседневные контакты; дом 3;
- `negotiations` — обсуждение и договорённость один на один; дом 7;
- `groups_audience` — группа, сообщество, аудитория; дом 11;
- `public_speech_teaching` — выступление/преподавание; дом 9/10 + соответствующий context.

### 4.7. Здоровье

- `general_condition` — общее физическое состояние и тонус; дом 1;
- `symptoms_routine_treatment` — симптомы, режим, лечение, восстановительная рутина; дом 6;
- `recovery_isolation` — отдых, снижение активности, изоляция/стационарный контекст; дом 12 + подтверждающий context.

Дом 8 не является общей базой здоровья. Дом 12 сам по себе не означает скрытую болезнь. Диагнозы и конкретные медицинские события запрещены.

### 4.8. Дом и семья

- `family_roots` — семья, родители, корни, домашняя база; дом 4;
- `housing_property` — жильё, недвижимость, бытовое пространство; дом 4;
- `relocation` — переезд; дом 4 + movement-context через 3/9.

### 4.9. Поездки

- `local_travel` — короткая/локальная поездка; дом 3;
- `long_distance_foreign_travel` — дальняя поездка/заграница; дом 9.

Уран только модифицирует неожиданность; без 3/9 или явной travel-темы поездку не создаёт.

### 4.10. Творчество

- `self_expression` — творчество и авторское проявление; дом 5;
- `creative_work` — творческий проект как работа/публичный результат; 5 + 10;
- `private_inner_creativity` — творчество в уединении; 5 + 12.

Дом 12, Нептун или Уран без 5-го дома либо явного creative-context творчество не создают.

### 4.11. Учёба

- `skills_courses` — навык, курс, базовое обучение; дом 3;
- `higher_education_worldview` — высшее образование, сложные системы знания, философия; дом 9.

### 4.12. Друзья и планы

- `friends_community` — друзья, сообщества, единомышленники; дом 11;
- `collective_projects` — совместные проекты; дом 11 + project/work-context;
- `long_term_goals` — долгосрочные планы и направление развития; дом 11.

---

## 5. Правила resolver

Resolver выбирает `(sphere, facet|null)` детерминированно по приоритету:

1. конкретный `house` physical unit/group;
2. `technical_spheres`;
3. явный normalized context/alias события;
4. source/target planets как модификаторы и tie-break.

Planet-only запрещён для узких facets.

Если sphere определена, а facet нет:

```text
sphere = resolved
facet = null
```

Если sphere не определяется, signal не публикуется и увеличивается существующий `group_without_sphere_count`/соответствующий unmapped audit. На acceptance replay таких случаев должно быть 0.

Неизвестный factor не падает в `work` и не получает иной fallback.

Одинаковый набор physical facts при любой перестановке должен давать одинаковые event IDs, group IDs, sphere, facet, polarity и selection order. Producer duplicate не даёт второй голос.

---

## 6. Изменения канонов

### 6.1. `grace/canon/spheres.v1.yml`

**Не менять его назначение и структуру.** Это технический scoring-канон девяти кластеров.

Допустимы только точечные исправления, если реализация выявит фактическую ошибку технического scoring; такие изменения не входят в это ТЗ и требуют отдельного решения.

### 6.2. Новый `grace/canon/product_spheres.v1.yml`

Создать единый product-канон, содержащий:

- порядок и labels 12 product spheres;
- facets;
- допустимые houses;
- допустимые technical/context keys;
- planet modifiers/tie-breaks;
- правила приоритета;
- запреты planet-only;
- rename/migration aliases только для одноразовой миграции данных (`money`, `shopping`), но не для runtime output.

Не создавать `product_spheres.v2.yml` и отдельный `sphere_facets`-канон.

### 6.3. `grace/canon/today_convergence.v1.yml`

Изменить текущий `sphere_projection`:

- canonical order заменить на новые 12 keys;
- удалить fan-out registries `technical_to_product`, `technical_alias_to_product`, `planet_to_product`, `planet_sphere_limits`;
- ссылаться на `product_spheres.v1.yml` как источник product projection;
- зафиксировать one group → one sphere → one facet/null;
- удалить secondary sphere;
- не менять significance, eligibility, grouping, hero, tone и birth-time sections;
- сохранить существующий status либо синхронно изменить strict-loader expectation; YAML и loader не должны расходиться.

### 6.4. `today_convergence_themes.v1.yml`

Themes остаются только для physical direct-star link. Не использовать их как продуктовый реестр. Менять лишь при необходимости покрыть реальные technical keys 4/5/11 домов.

---

## 7. Изменения backend runtime

### 7.1. `today_convergence_canon.py`

- загрузить и строго валидировать `product_spheres.v1.yml`;
- проверить ровно 12 keys в утверждённом порядке;
- проверить unique facets и houses 1..12;
- удалить helpers старого fan-out;
- реализовать один resolver внутри текущего canon/projection-модуля;
- синхронно изменить strict checks, которые сейчас требуют старый `frozen_w1` shape и девять `sphere_projection` keys;
- неизвестные mapping values fail closed.

Новый отдельный runtime-сервис для facets не создавать.

### 7.2. `today_convergence_units.py`

В `CanonicalUnit`:

- удалить `product_spheres`;
- **добавить новое поле** `technical_spheres: tuple[str, ...]` — сейчас оно есть только в `RawPhysicalFact` и теряется при normalization;
- сохранить `house`, source/target, theme keys и прочие physical fields;
- не вычислять product sphere на unit-build boundary;
- не менять canonical identity, significance, eligibility, orb и birth-time rules.

Sphere/facet не входят в `canonical_event_id`.

### 7.3. `today_convergence_groups.py`

- direct-star, independence, C1 и group identity оставить без изменений;
- после формирования physical group вызвать resolver;
- заменить `primary_sphere/secondary_sphere` на `sphere/facet`;
- не клонировать group;
- при unresolved sphere не публиковать group и увеличить audit;
- `group_id` зависит только от member event IDs.

### 7.4. `today_convergence_selection.py`

Для convergence state:

- убрать sphere-diversity gate;
- убрать cap на количество distinct spheres;
- сохранить максимум 3 selected convergence groups;
- repeated sphere не является причиной исключения;
- `selected_spheres` — уникальный список сфер уже выбранных signals, не критерий selection.

Для quiet day сохранить текущий контракт:

- `main_event` — 0..1;
- `impulses` — 0..3;
- суммарно возможно до 4 content blocks;
- repeated sphere не является причиной исключения;
- все events получают `sphere/facet` тем же resolver.

Не формулировать общий cap как «три сигнала для всех states».

### 7.5. `today_convergence_tone.py`

Формулу не менять. Polarity остаётся на physical group/unit и передаётся вместе с `sphere/facet`.

### 7.6. Wire projection и validators

В `apps/api/app/schemas/today_convergence.py` и связанных projection builders:

- заменить `primarySphere/secondarySphere` на `sphere/facet`;
- удалить `group_sphere_distinct` validator;
- удалить `sphere_union_cap`; payload ограничивается количеством groups/events, а не числом distinct spheres;
- сохранить event-reference, content-state, time-precision и остальные fail-closed validators;
- обновить event/main/impulse/group models согласованно.

### 7.7. Narrative и sanitizer

В prompt передавать:

- `sphere`;
- `facet|null`;
- `polarity`;
- source fact IDs;
- houses/planets как deterministic grounding.

Capability rule:

- при `capabilities.houses=true` дома можно использовать и называть в тексте;
- при `capabilities.houses=false` house data разрешена только как внутреннее grounding resolver, но **не передаётся модели как разрешённый claim и не может упоминаться в output**;
- существующие regex/capability guards не ослаблять.

Обновить `narrative_sanitizer.py`:

- заменить старые sphere patterns/related-spheres на новые 12 keys и facets;
- удалить разрешённые связи `money↔shopping`, `decisions` и другие старые исключения;
- запретить foreign sphere/facet и распространение polarity на всю sphere;
- `facet=null` допускает только общий язык sphere;
- одна regeneration, затем `summary=null`/существующий honest pending.

### 7.8. Страницы сфер и drilldown

Атомарно обновить:

- `today_sphere_page_service.py`;
- `today_sphere_drilldown.py` и его schema/tests, даже если текущий frontend endpoint не использует;
- natal narrative cache keys/fixtures для новых sphere keys;
- все места, где ожидаются primary/secondary sphere.

---

## 8. Контракты, frontend и check-in

### 8.1. Wire versioning

Не вводить несуществующий `contract_version`.

Принято:

- `TodayConvergencePayload.schema_version`: bump `1 → 2`;
- `formula_version`: оставить `today-convergence-2`, поскольку physical hero/formula не меняется;
- `calculation_version`: bump на следующую текущую project revision, поскольку projection/selection semantics изменились;
- canon hash изменится из-за новых/изменённых канонов;
- legacy schema union и aliases не поддерживать.

Пересобрать OpenAPI, generated TypeScript/Zod и registry snapshots штатными командами проекта.

### 8.2. ProductSphereKey и labels

Обновить единый literal union и все его consumers. Явно заменить `money → finance`, удалить `decisions/shopping`, добавить `home_family/friends_goals`.

Проверить и синхронно изменить минимум:

- `lib/display/sphere-labels.ts`;
- `today-formatters.tsx`;
- `lib/contracts/today.ts`;
- generated `_generated.ts`/Zod;
- icons и navigator order;
- fixtures, visual snapshots, e2e;
- dynamic `[key]` sphere route validation.

Не писать в ТЗ «удалить отдельные routes решений/покупок»: отдельных routes нет.

### 8.3. Tile summary

Frontend группирует выбранные signals по sphere:

- все supportive → `поддержка`;
- все tense → `напряжение`;
- наличие обеих сторон или хотя бы одного `mixed` → единый UI-label `поддержка + напряжение`;
- отдельный старый label `смешанно` для sphere tile удалить/заменить;
- polarity каждого signal остаётся видимой отдельно.

### 8.4. Check-in persisted data

`evening_checkins.observed_spheres` реально хранится в JSON и использует тот же ProductSphereKey. Поэтому заявление «миграция данных не требуется» к check-in неприменимо.

До реализации выполнить preflight query/count по значениям:

```text
money
decisions
shopping
```

Добавить одноразовую Alembic/data migration:

- `money → finance`;
- `shopping → finance`;
- `decisions` удалить из observed list, потому что предмет решения из старого key восстановить нельзя;
- дедуплицировать список после mapping;
- неизвестные keys не угадывать: зафиксировать count и fail migration либо явно очистить только после owner approval;
- обновить check-in Pydantic schemas, service, frontend, tests и generated contracts.

Если preflight докажет, что таблица пуста во всех deploy environments, migration всё равно должна быть безопасной no-op либо в verification evidence должно быть явно зафиксировано решение не создавать её.

---

## 9. Tests

Обновить существующие suites; отдельный framework не создавать.

### 9.1. Canon/unit/grouping

Доказать:

- `spheres.v1.yml` продолжает грузиться как технический scoring-канон;
- `product_spheres.v1.yml` содержит ровно 12 новых keys;
- planet-only не создаёт узкий facet;
- `CanonicalUnit` хранит `technical_spheres`, но не product sphere;
- sphere/facet не меняют event/group identity;
- 2 дом → finance/personal_money;
- 8 дом не становится obligation без context;
- 3/9 маршрутизируются по context между travel/study/documents/communication;
- Уран без 3/9 не создаёт travel;
- Нептун/Уран без 5 не создают creativity;
- две groups одной sphere остаются двумя groups.

Все существующие direct-star/C1/permutation/duplicate tests сохранить зелёными.

### 9.2. Selection/wire/tone

Доказать:

- supportive personal_money и tense financial_obligations выбираются одновременно;
- repeated finance не исключается;
- convergence cap = 3 groups;
- quiet cap = main 0..1 + impulses 0..3;
- `selected_spheres` содержит finance один раз;
- wire принимает повтор sphere и не применяет sphere-union cap;
- group polarity/dayTone не меняются;
- tile summary строится из signal polarities.

### 9.3. Narrative

Focused fixtures:

- personal_money не пишет о кредите/налоге;
- financial_obligations не объявляет напряжение во всех финансах;
- facet=null не превращается в покупку/долг;
- houses=false не допускает упоминание домов;
- health не пишет диагноз;
- foreign sphere/facet вызывает reject;
- updated sanitizer не отклоняет валидные новые keys.

### 9.4. Frontend/check-in/e2e

- правильный порядок 12 tiles;
- нет decisions/shopping/money;
- есть finance/home_family/friends_goals;
- два signals одной sphere видны на одном tile и в drilldown;
- check-in принимает новые keys;
- migration mapping/dedup покрыты PostgreSQL и unit tests;
- visual baselines/fixtures заменены.

---

## 10. Replay и доказательство устойчивости

### 10.1. Обязательная синхронизация analysis pipeline

Текущий `corpus_replay.py` использует analysis-копию canon/projection, а не production `today_convergence_groups.py`. Поэтому одновременно изменить:

- `analysis/convergence_canon.py`;
- связанные analysis helpers/tests;
- `analysis/corpus_replay.py` aggregation/report;
- при необходимости `ablation_harness.py`, только в части product projection, не физической формулы.

Production и analysis resolver должны проходить parity fixtures на одинаковых inputs.

### 10.2. Расширить replay output

Добавить daily/aggregate evidence:

- canonical event IDs;
- group IDs и member IDs;
- driver keys;
- hero anchor/confirmation IDs;
- evidence level;
- group polarity;
- state/dayTone;
- selected group/event IDs;
- counts по sphere/facet;
- `facet=null` count;
- repeated-sphere selected count;
- `group_without_sphere`/unmapped count;
- occurrences старых keys.

Без этих полей replay не считается доказательством данного ТЗ.

### 10.3. Fingerprint и baseline procedure

Добавить в `FINGERPRINT_FILES` минимум:

- `grace/canon/product_spheres.v1.yml`;
- `grace/canon/today_convergence.v1.yml`;
- `grace/canon/today_convergence_themes.v1.yml`;
- production canon/units/groups/selection files;
- analysis canon/replay files.

Порядок локальной работы в одном branch:

1. сначала внести только replay instrumentation/parity additions, не меняя production semantics;
2. regenerate manifest для этой instrumented baseline и выполнить baseline run;
3. сохранить baseline aggregate/signatures и commit SHA в verification artifacts;
4. реализовать product taxonomy/runtime изменения;
5. regenerate candidate manifest с новым fingerprint;
6. выполнить candidate run и сравнить physical signatures.

Разные fingerprints baseline/candidate ожидаемы и фиксируют lineage. Сравнение выполняется по одинаковым chart IDs, seed, датам и physical signature fields. `--allow-source-drift` для acceptance запрещён.

Это порядок выполнения внутри одного рабочего пакета; промежуточный production merge не требуется.

### 10.4. Smoke

```bash
cd /opt/solarsage-astro
apps/api/.venv/bin/python \
  docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py \
  --output-dir /var/tmp/spheres-smoke \
  --residues 0,1,2,3,4 \
  --limit-charts 5 \
  --from-date 2026-07-01 \
  --to-date 2026-07-30 \
  --workers 4
```

Промежуточный отдельный gate `20×365` удалить. Нужны smoke и full acceptance; распределения анализируются в full report.

### 10.5. Full acceptance replay

```bash
apps/api/.venv/bin/python \
  docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py \
  --output-dir /var/tmp/spheres-full \
  --residues 0,1,2,3,4 \
  --from-date 2025-01-01 \
  --to-date 2026-12-31 \
  --workers 8
```

Корпус:

- 120 synthetic charts;
- 730 дней;
- exact + 4 buckets + unknown.

Acceptance gates:

- chart errors = 0;
- invalid ledger = 0;
- unmapped/group-without-sphere = 0;
- old keys occurrences = 0;
- invalid facet = 0;
- one group → one sphere;
- group clone count = 0;
- repeated-sphere groups не теряются из-за diversity;
- physical event IDs, group IDs/members, driver keys, hero pair, evidence level, group polarity, state и dayTone совпадают с baseline;
- разрешённый delta: sphere/facet, selected top-N там, где раньше срабатывал diversity-gate, selected_spheres, narrative и UI labels.

Если изменились physical groups, hero, state или dayTone, реализация останавливается: product projection вмешалась в запрещённую часть формулы.

---

## 11. Порядок реализации

1. Добавить replay instrumentation/parity и снять baseline.
2. Создать `product_spheres.v1.yml`; `spheres.v1.yml` оставить техническим.
3. Изменить `today_convergence.v1.yml`, themes при необходимости и strict loader.
4. Добавить `technical_spheres` в CanonicalUnit; убрать product projection из unit.
5. Переделать group projection на `sphere/facet`.
6. Убрать diversity-gate и обновить per-state selection caps.
7. Обновить wire validators, schema version и generated contracts.
8. Обновить narrative/capability/sanitizer.
9. Обновить sphere page/drilldown/natal cache consumers.
10. Выполнить check-in preflight и data migration.
11. Обновить frontend labels/types/navigator/fixtures/e2e.
12. Прогнать focused backend, analysis, contract, frontend и PostgreSQL tests.
13. Прогнать smoke и full replay; зафиксировать comparison report.

Не мержить состояние, где backend, generated contracts и frontend ожидают разные keys/shapes.

---

## 12. Вне scope

Не менять:

- aspect/orb thresholds;
- significance/eligibility;
- direct-star grouping и independence;
- rare anchors и hero C1;
- tone formula;
- birth-time publication rules;
- sidecar/ephemeris calculations;
- существующие per-state content caps, кроме удаления sphere-diversity ограничения.

Не создавать:

- compatibility layer;
- parallel v2 runtime;
- отдельный facets service;
- универсальный ontology engine;
- shadow/canary инфраструктуру.

---

## 13. Критерии приёмки

Работа принята, когда одновременно:

1. `spheres.v1.yml` остался техническим scoring-каноном.
2. `product_spheres.v1.yml` является единственным источником 12 product spheres/facets.
3. В runtime/UI ровно утверждённые 12 keys; `money/decisions/shopping` отсутствуют.
4. `finance`, `home_family`, `friends_goals` работают end-to-end.
5. Physical group получает одну sphere и facet/null; secondary sphere удалена.
6. Sphere/facet не входят в event/group identity.
7. Два signals одной sphere сохраняются одновременно и имеют собственные polarities.
8. Wire validators принимают repeated sphere и не имеют sphere-union cap.
9. Narrative соблюдает capability, sphere, facet, polarity и fact IDs.
10. Check-in persisted values безопасно преобразованы либо доказано отсутствие строк.
11. Production и analysis projection имеют parity fixtures.
12. Focused backend/frontend/contract/PostgreSQL/analysis tests зелёные.
13. Full replay проходит gates и не меняет physical groups, hero, state и dayTone.
14. Старые keys, fixtures, generated unions и compatibility branches удалены.

После выполнения текущая реализация остаётся единственной актуальной версией продукта.