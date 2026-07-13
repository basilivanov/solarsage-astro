# Stage B2B1 — strict content canons, personal fact pack and machine tone

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый HEAD/origin: `cd27d1a8056eef92737e992c1b0998423331734b`
Parent: `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md`, sections 5, 8, 10
Decomposition: `63_STAGE_B2B_DECOMPOSITION_AND_INVARIANTS.md`

## 0. Роль и режим выполнения

Реализовать только B2B1: три versioned content canon, strict typed loading,
deterministic personal fact pack и deterministic per-horizon machine tone.

Кодер выполняет реализацию в текущей ветке. Архитектор проводит ревью. Не
запускать субагентов. До отдельного architect acceptance запрещены:

```text
git add
git commit
git push
```

Не ждать уточнений по контенту и не сочинять альтернативную copy: exact initial
v1 wording и rules ниже являются частью ТЗ.

## 1. Preflight

До изменений выполнить:

```bash
git status --short --branch
git diff --cached --name-only
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
pnpm contracts:check
```

Ожидание:

```text
branch: preview/solarsage-v2-human-first-navigator-ux
HEAD == origin feature == cd27d1a8056eef92737e992c1b0998423331734b
index: empty
contracts:check: PASS
```

Допустимы только эти unrelated untracked paths; не читать, не форматировать, не
добавлять в index и не удалять:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Если tracked tree уже изменён вне allowlist section 3, остановиться с callback
`BLOCKED_B2B1_DIRTY_TRACKED_TREE` и exact path list.

## 2. Scope boundary

### 2.1 Входит

- strict language/action/personal-pattern YAML canons;
- strict schemas and cross-canon validation;
- fail-fast startup validation;
- dedicated content-canon version helper;
- internal personal fact pack schema/service;
- finite natal predicate matcher;
- selected activation-linked sphere facts;
- per-horizon tone schema/service;
- focused tests, privacy proof, determinism proof, full API baseline comparison.

### 2.2 Не входит

- `TodayV2HorizonsBlock` generation;
- changes to `today_horizons.py` or any public schema;
- `TodayService`, `SemanticV2Service`, `CalendarService`;
- `TodayV2Block.horizons` population;
- `ConcreteAdviceBlock` construction changes;
- frontend, OpenAPI, TS/Zod generation output changes;
- sidecar/shared contracts;
- claim validator, coverage corpus, LLM;
- cache/audit/content/calculation/scoring version changes;
- logging events;
- DB/migrations/env/systemd/nginx/ports;
- commit/push.

Production behavior after this task remains byte-compatible at the public API
boundary: `horizons` is still not populated by runtime orchestration.

## 3. Exact file allowlist

Разрешены только:

```text
grace/canon/horizon_language.ru.v1.yml
grace/canon/horizon_actions.ru.v1.yml
grace/canon/personal_patterns.ru.v1.yml

apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/personal_fact_pack.py
apps/api/app/schemas/horizon_tone.py

apps/api/app/services/canon_service.py
apps/api/app/services/horizon_content_canon_service.py
apps/api/app/services/personal_fact_pack_service.py
apps/api/app/services/horizon_tone_service.py

apps/api/tests/_horizon_content_testkit.py
apps/api/tests/test_canon_service.py
apps/api/tests/test_horizon_content_canon_service.py
apps/api/tests/test_personal_fact_pack_service.py
apps/api/tests/test_horizon_tone_service.py

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/63_STAGE_B2B_DECOMPOSITION_AND_INVARIANTS.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/64_STAGE_B2B1_CONTENT_CANONS_FACT_PACK_TONE_TZ.md
```

Не менять `apps/api/app/schemas/__init__.py`, `contract_registry.py`, generated
OpenAPI/TS/Zod, `horizon_selection.v1.yml` или B2A implementation.

Если для корректной реализации якобы нужен ещё path, не расширять scope самому:
вернуть `BLOCKED_B2B1_SCOPE_EXTENSION_REQUIRED` с path/reason.

## 4. GRACE, purity and privacy

Every new Python file must include accurate:

```text
AI_HEADER
START_MODULE_CONTRACT / END_MODULE_CONTRACT
START_MODULE_MAP / END_MODULE_MAP
START_BLOCK / END_BLOCK
START_FUNCTION_CONTRACT / END_FUNCTION_CONTRACT
```

для каждого non-trivial public/private helper, matcher и service method.

All new schemas/services are internal and pure:

```text
no DB
no network
no sidecar
no LLM
no env/settings
no random
no subprocess
no mutable server clock
no logging side effects
```

Forbidden in PersonalFactPack, exception text and test callback:

- `ActivationEvidence.evidence` body;
- activation/scoring `.debug` objects;
- first name, gender, city, coordinates, birth date/time/timezone;
- natal sign, exact house, degree, longitude, aspect type or orb as raw values;
- prior LLM text;
- user ID/auth/session data.

Structural planet names in generic source IDs are allowed. Example:

```text
natal:planet:saturn
natal:aspect:pluto:saturn
```

The following is forbidden because it leaks matched values:

```text
natal:saturn:aquarius:house10
natal:moon:pluto:opposition:orb1.05
```

## 5. Content-canon schema and loader architecture

Create `apps/api/app/schemas/horizon_content_canon.py`.

### 5.1 Base model

All canon models use a shared internal base:

```py
ConfigDict(
    extra="forbid",
    frozen=True,
    hide_input_in_errors=True,
)
```

Do not subclass public `CamelModel`; YAML keys are explicit snake_case internal
configuration.

Use typed `Literal` aliases for:

```text
horizon: long | medium | fast
tone: supportive | neutral | tense | mixed
timing state: upcoming | building | active | exact | peaked | fading | background
product sphere: exact 12 B1 keys
theme: exact 10 B2A keys
technique: exact 13 B2A known techniques
fact kind: strength | risk | profile | natal | sphere
claim safety class: reflection | reversible_experiment | low_stakes_communication | pacing | guardrail
template action intent: exact positive/avoid allowlists in section 7.2
forbidden policy intent: exact separate forbidden allowlist in section 7.2
natal predicate type: planet_in_sign | planet_in_house | aspect
```

Import/reuse B1/B2A aliases/constants where this does not create a cycle.
Never copy an open-ended `str` where a closed set already exists.

### 5.2 Three top-level models

Required models:

```text
HorizonLanguageCanon
HorizonActionsCanon
PersonalPatternsCanon
HorizonContentCanonBundle
```

Each file requires exact:

```yaml
schema_version: <file-specific literal>
version: v1
locale: ru
```

File-specific schema versions:

```text
horizon_language.ru.v1
horizon_actions.ru.v1
personal_patterns.ru.v1
```

### 5.3 Loader

Create `apps/api/app/services/horizon_content_canon_service.py` with only these
public entrypoints:

```py
load_horizon_content_canons(canon_dir: Path | None = None) -> HorizonContentCanonBundle
get_horizon_content_canon_versions() -> dict[str, str]
clear_horizon_content_canon_cache_for_tests() -> None
```

Default directory is repo-relative `grace/canon`, never cwd-dependent.

Caching:

```text
default directory: lru_cache(maxsize=1)
explicit resolved directory: lru_cache(maxsize=32)
```

Failure policy:

- missing file -> `CanonValidationError` with path and `missing canon file`;
- malformed YAML -> path and `malformed YAML`;
- unreadable -> path and `unreadable canon file`;
- Pydantic/cross-canon failure -> path/bundle structural location and compact
  reason;
- never include raw YAML value/copy in error text;
- no fallback/default canon.

Version helper returns exactly:

```py
{
    "horizon_language_ru": "v1",
    "horizon_actions_ru": "v1",
    "personal_patterns_ru": "v1",
}
```

Do not merge this mapping into existing `get_canon_versions()` in B2B1.

### 5.4 Cross-canon validation

Bundle validation must prove:

1. all three locales are exactly `ru` and versions exactly `v1`;
2. language technique keys exactly equal B2A known technique keys;
3. language theme keys exactly equal the 10 themes in section 6.4;
4. language sphere keys exactly equal all 12 public product spheres;
5. language tone/timing/horizon keys exactly equal their enums;
6. action theme keys exactly equal language theme keys;
7. action template IDs are globally unique;
8. every template references only known tones/spheres/safety classes/intents;
9. every theme+horizon has enough `do`/`avoid` templates for B1 counts;
10. every action template sphere set intersects the owning theme sphere set;
11. every personal pattern theme/sphere/statement key exists;
12. pattern kind equals referenced personal statement kind;
13. every strength/risk personal statement is referenced by exactly one v1
    pattern rule, while sphere fact statement keys are validated separately;
14. every allowed template placeholder belongs to the exact placeholder set;
15. no unknown or missing key is silently accepted.

## 6. `horizon_language.ru.v1.yml` exact content

### 6.1 Horizon labels

```yaml
horizons:
  long:
    eyebrow: Долгий цикл
    actions_heading: Что перестраивать
    avoid_heading: Чего не закреплять
  medium:
    eyebrow: Текущий период
    actions_heading: Что попробовать
    avoid_heading: Чего пока не делать
  fast:
    eyebrow: Быстрый триггер
    actions_heading: Что сделать сейчас
    avoid_heading: Что лучше отложить
```

### 6.2 Tone and timing labels

```yaml
tone_labels:
  supportive: Поддерживающий фон
  neutral: Нейтральный фон
  tense: Напряжённый фон
  mixed: Смешанный фон

timing_state_labels:
  upcoming: Период ещё впереди
  building: Набирает силу
  active: Активно сейчас
  exact: Точный пик сейчас
  peaked: Пик уже пройден
  fading: Влияние постепенно ослабевает
  background: Фон уже действует
```

Date labels later use explicit target timezone and these exact templates:

```yaml
timing_templates:
  range: "С {active_from} по {active_until}"
  peak: "Точный пик — {exact_at}"
  valid_until: "Актуально до {active_until}"
  long_valid_until: "Ориентир до {active_until}"
  fast_eases: "Короткий пик ослабеет к {active_until}"
```

Allowed placeholders are exactly:

```text
active_from active_until exact_at range_label peak_label state_label
theme_label sphere_label target_label source_label
```

### 6.3 Technique language

Each technique entry has exactly:

```text
label
what_it_is
why_it_matters_template
```

Exact Russian content:

| technique | label | what_it_is | why_it_matters_template |
|---|---|---|---|
| `annual_profection` | Годовая профекция | Профекция — символический годовой цикл, который выделяет одну жизненную тему и связанную с ней планету-управителя. | В выбранном году профекция выделяет тему «{theme_label}». Её период: {range_label}. |
| `monthly_profection` | Месячная профекция | Месячная профекция уточняет годовую тему и показывает, какая её часть выходит на первый план в течение нескольких недель. | Сейчас месячная профекция усиливает тему «{theme_label}». Окно: {range_label}. |
| `firdar_major` | Большой период фирдара | Фирдар — последовательность длинных планетарных периодов, которая описывает устойчивый фон этапа жизни, а не одно событие. | Текущий большой период фирдара удерживает тему «{theme_label}» в длительном фокусе. Период: {range_label}. |
| `firdar_minor` | Малый период фирдара | Малый период фирдара уточняет длинный фон и показывает, какая его часть заметнее в текущем отрезке. | Малый период фирдара усиливает тему «{theme_label}» внутри более длинного цикла. Период: {range_label}. |
| `solar_return` | Соляр | Соляр — карта на момент ежегодного возвращения Солнца, которая задаёт темы личного года. | В текущем соляре заметнее тема «{theme_label}». Годовое окно: {range_label}. |
| `lunar_return` | Лунар | Лунар — карта возвращения Луны, описывающая более короткий эмоциональный и бытовой цикл. | В текущем лунаре сильнее выделена тема «{theme_label}». Окно: {range_label}. |
| `solar_arc` | Солнечная дуга | Солнечная дуга — символическая техника медленных сдвигов, которая показывает длительно созревающую тему. | Солнечная дуга связывает текущий этап с темой «{theme_label}». Период: {range_label}. |
| `secondary_progression` | Вторичная прогрессия | Вторичная прогрессия — символическая техника, которая описывает постепенное внутреннее развитие темы. | Прогрессия делает тему «{theme_label}» более заметной в текущем этапе. Период: {range_label}. |
| `eclipse_window` | Окно затмения | Окно затмения — ограниченный период вокруг затмения, когда связанная тема может восприниматься острее обычного. | Для выбранной даты окно затмения связано с темой «{theme_label}». Окно: {range_label}. |
| `transit_to_natal` | Транзит к натальной планете | Транзит показывает, как текущее положение планеты временно взаимодействует с положением планеты в вашей натальной карте. | {source_label} затрагивает {target_label} и временно усиливает тему «{theme_label}». Окно: {range_label}. |
| `transit_to_angle` | Транзит к углу карты | Такой транзит связывает текущее движение планеты с одной из опорных точек натальной карты: ASC, MC, DSC или IC. | {source_label} затрагивает {target_label}, поэтому тема «{theme_label}» заметнее в этом окне: {range_label}. |
| `transit_to_lot` | Транзит к жребию | Такой транзит связывает текущую планету с расчётной точкой карты и используется только как дополнительный тематический сигнал. | {source_label} затрагивает {target_label} и добавляет сигнал к теме «{theme_label}». Окно: {range_label}. |
| `transit_planet_in_house` | Транзит планеты по дому | Эта техника показывает, в какой области натальной карты сейчас движется планета и где её тема становится заметнее. | {source_label} проходит через область, связанную с темой «{theme_label}». Окно: {range_label}. |

Do not use `ActivationEvidence.evidence` as replacement or suffix.

### 6.4 Theme language

Theme keys are exactly:

```text
communication_learning_documents
structure_boundaries_control
relationships_values_closeness
resources_security
energy_body_pacing
home_belonging
inner_clarity_recovery
direction_growth_meaning
creativity_visibility
change_innovation
```

Each theme entry contains `label`, `headline`, `intro_body`, and exact
`long|medium|fast` objects with `title` and `plain_explanation`.

#### `structure_boundaries_control`

```text
label: Опора, границы и контроль
headline: Сейчас перестраивается способ удерживать опору
intro_body: Длинный цикл меняет правила ответственности, текущий период проверяет границы, а короткий триггер показывает, где давление усиливает потребность всё контролировать.
long.title: Перестройка опоры и ответственности
long.plain_explanation: Это медленный фон: он не требует немедленного решения, но постепенно меняет то, на что вы опираетесь и какие обязательства готовы считать своими.
medium.title: Проверка границ на практике
medium.plain_explanation: В ближайшие недели тема проявляется через конкретные правила, роли и договорённости, которые можно проверить небольшими изменениями.
fast.title: Короткий пик реакции на давление
fast.plain_explanation: Сегодня важнее не скорость, а пауза между внешним давлением и вашим решением, чтобы не спутать принципиальную границу с первой реакцией.
```

#### `communication_learning_documents`

```text
label: Формулировки, обучение и договорённости
headline: Сейчас особенно важен способ назвать и проверить главное
intro_body: Длинный цикл меняет привычный способ думать и договариваться, текущий период требует более точной формулировки, а короткий триггер показывает, где поспешный ответ создаёт лишний шум.
long.title: Перестройка способа думать и объяснять
long.plain_explanation: Длительный фон постепенно меняет ваши правила работы с информацией, обучением и важными договорённостями.
medium.title: Окно для уточнения и проверки
medium.plain_explanation: В ближайшие недели полезнее проверять смысл небольшими шагами: черновиком, вопросом и одной подтверждённой договорённостью.
fast.title: Короткий пик в словах и реакции
fast.plain_explanation: Сегодня одна неточная фраза может весить больше обычного, поэтому сначала стоит отделить факт от интерпретации.
```

#### `relationships_values_closeness`

```text
label: Близость, ценности и взаимность
headline: Сейчас уточняется, на чём держится взаимность
intro_body: Длинный цикл меняет критерии близости и ценности, текущий период проверяет договорённости, а короткий триггер делает заметнее тон, дистанцию и реакцию на неопределённость.
long.title: Пересборка критериев близости
long.plain_explanation: Медленный фон помогает заметить, какие формы взаимности и уважения к границам действительно устойчивы для вас.
medium.title: Проверка договорённостей в отношениях
medium.plain_explanation: В ближайшие недели важны не догадки о другом человеке, а один ясный вопрос, наблюдаемая реакция и конкретная договорённость.
fast.title: Короткий пик чувствительности к тону
fast.plain_explanation: Сегодня реакция на дистанцию или формулировку может быть острее, поэтому вывод лучше делать после уточнения, а не по первому впечатлению.
```

#### `resources_security`

```text
label: Ресурсы, устойчивость и цена решений
headline: Сейчас меняется способ создавать чувство устойчивости
intro_body: Длинный цикл пересматривает опору на ресурсы, текущий период проверяет критерии достаточности, а короткий триггер показывает, где тревога подталкивает к лишнему решению.
long.title: Перестройка ресурсной опоры
long.plain_explanation: Этот фон постепенно меняет правила, по которым вы распределяете время, деньги, внимание и запас прочности.
medium.title: Проверка одного ресурсного решения
medium.plain_explanation: В ближайшие недели полезен небольшой измеримый эксперимент вместо полной перестройки бюджета, условий или обязательств.
fast.title: Короткий импульс вернуть контроль
fast.plain_explanation: Сегодня лучше отделить реальную необходимость от желания немедленно снять неопределённость покупкой, обещанием или резким отказом.
```

#### `energy_body_pacing`

```text
label: Энергия, нагрузка и темп
headline: Сейчас важно точнее распределять усилие
intro_body: Длинный цикл меняет отношение к нагрузке, текущий период проверяет рабочий темп, а короткий триггер показывает, где раздражение или спешка заставляют расходовать больше сил, чем нужно.
long.title: Перестройка устойчивого темпа
long.plain_explanation: Медленный фон предлагает пересмотреть не отдельный рывок, а привычную систему нагрузки, восстановления и запаса сил.
medium.title: Эксперимент с объёмом и ритмом
medium.plain_explanation: В ближайшие недели полезно изменить один параметр нагрузки и наблюдать результат, не делая медицинских выводов из астрологического сигнала.
fast.title: Короткий пик спешки или раздражения
fast.plain_explanation: Сегодня точнее сначала снизить лишнюю интенсивность, а затем решать, действительно ли нужно ускоряться.
```

#### `home_belonging`

```text
label: Дом, принадлежность и личное пространство
headline: Сейчас уточняется, что даёт ощущение своего места
intro_body: Длинный цикл меняет представление об опоре и принадлежности, текущий период проверяет бытовые правила и границы, а короткий триггер показывает, где неудобство быстро превращается в жёсткую реакцию.
long.title: Пересборка ощущения дома и опоры
long.plain_explanation: Этот фон касается не обязательного переезда или события, а более медленного пересмотра условий, в которых вам легче сохранять устойчивость.
medium.title: Проверка бытовой договорённости
medium.plain_explanation: Если сейчас меняется домашний порядок, полезнее проверить одно правило или распределение ответственности, чем менять всё сразу.
fast.title: Короткий пик чувствительности к пространству
fast.plain_explanation: Сегодня раздражение из-за порядка или границ лучше сначала назвать конкретно, не превращая его в общий вывод о ситуации.
```

#### `inner_clarity_recovery`

```text
label: Внутренняя ясность и восстановление
headline: Сейчас особенно важно отличать сигнал от перегруза
intro_body: Длинный цикл меняет способы восстанавливать ясность, текущий период показывает повторяющийся источник шума, а короткий триггер делает заметнее то, что требует паузы, а не немедленного вывода.
long.title: Перестройка способов возвращать ясность
long.plain_explanation: Медленный фон предлагает наблюдать, какие условия действительно помогают вам собраться, без диагнозов и обещаний гарантированного результата.
medium.title: Проверка одного источника перегруза
medium.plain_explanation: В ближайшие недели полезно убрать или ограничить один повторяющийся источник шума и проверить эффект.
fast.title: Короткий пик внутреннего шума
fast.plain_explanation: Сегодня первая мысль может быть громче, чем точнее, поэтому решение лучше отделить от момента максимальной перегрузки.
```

#### `direction_growth_meaning`

```text
label: Направление, рост и смысл
headline: Сейчас уточняется, куда действительно стоит вкладываться
intro_body: Длинный цикл меняет представление о направлении, текущий период проверяет одну возможность, а короткий триггер показывает, где вдохновение легко перепутать с обязательством немедленно выбрать весь путь.
long.title: Пересмотр долгого направления
long.plain_explanation: Этот фон помогает заново определить критерии роста и смысла, не требуя немедленно менять работу, обучение или место жизни.
medium.title: Проверка направления малым шагом
medium.plain_explanation: В ближайшие недели полезнее провести один ограниченный тест интереса или возможности, чем заранее обещать себе весь маршрут.
fast.title: Короткий пик ожиданий
fast.plain_explanation: Сегодня сильная идея заслуживает записи и проверки, но не обязана сразу становиться крупным обязательством.
```

#### `creativity_visibility`

```text
label: Творчество, проявленность и оценка
headline: Сейчас меняется способ показывать результат
intro_body: Длинный цикл перестраивает отношение к проявленности, текущий период предлагает проверить формат, а короткий триггер делает реакцию на оценку заметнее обычного.
long.title: Перестройка отношения к проявленности
long.plain_explanation: Медленный фон касается устойчивого способа создавать и показывать результат, а не требования постоянно быть заметнее.
medium.title: Проверка формата на малой аудитории
medium.plain_explanation: В ближайшие недели полезно показать ограниченный черновик и собрать конкретную обратную связь, не связывая одну реакцию со всей своей ценностью.
fast.title: Короткий пик реакции на оценку
fast.plain_explanation: Сегодня лучше отделить полезный факт обратной связи от эмоциональной оценки всего результата.
```

#### `change_innovation`

```text
label: Изменение, свобода и новый способ
headline: Сейчас проверяется, что действительно пора менять
intro_body: Длинный цикл делает старое правило теснее, текущий период позволяет испытать новый способ, а короткий триггер усиливает желание изменить всё немедленно.
long.title: Пересмотр устаревшего правила
long.plain_explanation: Этот фон помогает заметить систему, которая больше не работает, но не требует разрушать её до появления проверяемой замены.
medium.title: Ограниченный эксперимент с новым способом
medium.plain_explanation: В ближайшие недели полезно изменить один элемент процесса и сравнить результат по заранее выбранному критерию.
fast.title: Короткий импульс резко всё изменить
fast.plain_explanation: Сегодня новизна может казаться единственным выходом, поэтому сначала стоит проверить самое маленькое обратимое изменение.
```

### 6.5 Product-sphere language

Every entry has `label`, `manifestation_title`, `manifestation_body`, and
`conditional: true`. Exact entries:

| key | label | manifestation_title | manifestation_body |
|---|---|---|---|
| `work` | Работа и статус | Где это может проявиться | Если сейчас меняются задачи, роль или объём ответственности, тема вероятнее проявится в правилах, сроках и договорённостях. |
| `money` | Деньги и ресурсы | Где это может проявиться | Если сейчас есть финансовое решение, тема вероятнее проявится в критериях достаточности, обязательствах и запасе прочности. |
| `documents` | Документы и формальности | Где это может проявиться | Если сейчас есть документ или формальная договорённость, тема вероятнее проявится в формулировках, сроках и распределении ответственности. |
| `relationships` | Отношения и близость | Где это может проявиться | Если сейчас есть важный разговор или договорённость с другим человеком, тема вероятнее проявится в тоне, взаимности и границах. |
| `sport` | Движение и тренировки | Где это может проявиться | Если на сегодня запланирована физическая нагрузка, тема вероятнее проявится в темпе, координации и выборе интенсивности. |
| `communication` | Общение | Где это может проявиться | Если сегодня есть важная переписка или разговор, тема вероятнее проявится в точности слов, вопросах и реакции на тон. |
| `health` | Самочувствие и режим | Где это может проявиться | Если вы оцениваете нагрузку или режим, тема вероятнее проявится в темпе и запасе сил; это не медицинский вывод или диагноз. |
| `decisions` | Решения | Где это может проявиться | Если сейчас нужно выбрать направление, тема вероятнее проявится в критериях решения, спешке и готовности оставить время на проверку. |
| `travel` | Поездки и маршруты | Где это может проявиться | Если сейчас планируется поездка или маршрут, тема вероятнее проявится в сроках, вариантах и необходимости перепроверить детали. |
| `creativity` | Творчество | Где это может проявиться | Если вы работаете над идеей или результатом, тема вероятнее проявится в формате, обратной связи и готовности показать черновик. |
| `study` | Обучение | Где это может проявиться | Если сейчас идёт обучение, тема вероятнее проявится в выборе фокуса, способе объяснения и проверке понимания. |
| `shopping` | Покупки | Где это может проявиться | Если сейчас рассматривается покупка, тема вероятнее проявится в различии между реальной необходимостью и желанием быстро снять неопределённость. |

All 12 bodies remain conditional. No code may remove `Если` while leaving the
claim unconditional.

The same section owns a separate machine lookup, not part of the 12
strength/risk personal statements:

```yaml
sphere_fact_statements:
  work: {statement_key: sphere.active.work, kind: sphere, text: Работа и статус}
  money: {statement_key: sphere.active.money, kind: sphere, text: Деньги и ресурсы}
  documents: {statement_key: sphere.active.documents, kind: sphere, text: Документы и формальности}
  relationships: {statement_key: sphere.active.relationships, kind: sphere, text: Отношения и близость}
  sport: {statement_key: sphere.active.sport, kind: sphere, text: Движение и тренировки}
  communication: {statement_key: sphere.active.communication, kind: sphere, text: Общение}
  health: {statement_key: sphere.active.health, kind: sphere, text: Самочувствие и режим}
  decisions: {statement_key: sphere.active.decisions, kind: sphere, text: Решения}
  travel: {statement_key: sphere.active.travel, kind: sphere, text: Поездки и маршруты}
  creativity: {statement_key: sphere.active.creativity, kind: sphere, text: Творчество}
  study: {statement_key: sphere.active.study, kind: sphere, text: Обучение}
  shopping: {statement_key: sphere.active.shopping, kind: sphere, text: Покупки}
```

Keys, statement keys, kinds and texts must agree exactly with the product-sphere
entries. These labels are looked up later; PersonalFactPack stores only the
statement key.

### 6.6 Personal statement catalog

The language canon owns exactly 12 initial statements. Each entry has `kind`
and `text`; key is stable and used by PersonalFact.

| statement key | kind | exact text |
|---|---|---|
| `strength.structure.steady_responsibility` | strength | Вы можете опираться на способность удерживать порядок, последовательность и ответственность в длинных задачах. |
| `strength.communication.structured_thinking` | strength | Вы можете опираться на умение раскладывать сложное на шаги и проверять смысл договорённости. |
| `strength.energy.measured_effort` | strength | Вам доступна способность дозировать усилие и сохранять направление после первого сопротивления. |
| `strength.relationships.tactful_clarity` | strength | Вы можете соединять ясность формулировки с вниманием к тону и позиции другого человека. |
| `strength.direction.broad_view` | strength | Вы можете опираться на способность видеть более широкий смысл, не теряя конкретной цели. |
| `strength.inner_clarity.name_reaction` | strength | Вам может помогать способность назвать переживание словами до того, как переходить к действию. |
| `risk.structure.control_under_pressure` | risk | Когда устойчивость нарушена, вы можете пытаться вернуть её через более жёсткий контроль, чем требует ситуация. |
| `risk.communication.overchecking` | risk | В неопределённости вы можете дольше перепроверять решение и становиться жёстче к формулировкам. |
| `risk.energy.increase_pressure` | risk | При сопротивлении вы можете усиливать нажим вместо того, чтобы сначала изменить темп или способ действия. |
| `risk.relationships.defensive_strictness` | risk | Когда договорённость неясна, вы можете становиться сдержаннее и строже к её условиям раньше, чем появятся все факты. |
| `risk.inner_clarity.intensity_before_clarity` | risk | При давлении реакция может усиливаться быстрее, чем успевает появиться ясность. |
| `risk.change.all_at_once` | risk | Когда свободы мало, вы можете стремиться изменить всё сразу, даже если достаточно одного точного изменения. |

No additional praise/risk sentence is permitted in v1. Different wording is a
canon change and must be reviewed, not embedded in Python.

### 6.7 Conditional language policy

```yaml
conditional_policy:
  required_prefixes:
    - "Если "
  forbidden_certainty_fragments:
    - обязательно произойдёт
    - точно случится
    - неизбежно
    - судьба требует
    - вы должны немедленно
    - гарантированно
  forbidden_high_stakes_fragments:
    - увольняйтесь
    - разрывайте отношения
    - берите кредит
    - продавайте
    - покупайте недвижимость
    - отменяйте лечение
    - меняйте лечение
    - ставьте диагноз
```

Validation is case-insensitive after whitespace normalization. These fragments
will be consumed by B2B2 claim validation; B2B1 validates the canon itself does
not contain forbidden language outside the explicit forbidden lists.

### 6.8 Tone rules

Tone numeric rules live in this canon, not Python constants:

```yaml
tone_rules:
  feature_weights:
    strength: 0.35
    contribution: 0.25
    convergence: 0.15
    impact: 0.25
  activation_weight: 0.75
  sphere_verdict_weight: 0.25
  verdict_values:
    good: 1.0
    neutral: 0.0
    caution: -0.6
    avoid: -1.0
  supportive_min: 0.30
  tense_max: -0.30
  mixed_opposing_min: 0.20
  rounding_digits: 6
```

Validation:

- `feature_weights` sum `1.0 ± 1e-9`;
- activation + sphere weights sum `1.0 ± 1e-9`;
- all feature/aggregate weights finite in `0..1`;
- verdict values finite in `-1..1`, ordered
  `good > neutral > caution > avoid`;
- `supportive_min > 0`, `tense_max < 0`;
- `mixed_opposing_min` in `0..1`;
- rounding digits exactly `6` for v1.

## 7. `horizon_actions.ru.v1.yml` exact policy

### 7.1 Template schema

Each action/avoid template has exactly:

```yaml
id: stable.global.id
text: Russian user-facing sentence
intent: <closed enum>
safety_class: <closed enum>
conditional: true|false
tones: [supportive, neutral, tense, mixed]
sphere_keys: [one or more product sphere keys]
```

Rules:

- `id` matches `^[a-z0-9][a-z0-9._-]{2,95}$`;
- IDs globally unique across do/avoid and all themes/horizons;
- text non-empty, no braces/placeholders in action body;
- normalized text globally unique;
- tones non-empty, unique, canonical order;
- sphere keys non-empty, unique and in the exact stable order stored by the
  owning theme entry;
- conditional `true` text must begin with an allowed conditional prefix;
- conditional `false` is permitted only for the exact reviewed v1 copy in this
  document; future free-form unknown-life assertions are a B2B2 claim-validator
  concern, not an NLP heuristic in the YAML loader;
- no template contains forbidden certainty/high-stakes fragment;
- all templates are low-risk and reversible.

### 7.2 Intent allowlist and safety mapping

Exact positive intents:

```text
reflect
plan
clarify
small_experiment
communicate_boundary
reduce_load
create_draft
record_observation
```

Exact avoid intents:

```text
postpone_major_decision
avoid_escalation
avoid_overcommitment
avoid_all_at_once
avoid_assumption
avoid_extra_intensity
```

Exact safety compatibility:

```yaml
safety_classes:
  reflection:
    allowed_intents: [reflect, clarify, record_observation]
    compatible_verdicts: [good, neutral, caution, avoid]
  reversible_experiment:
    allowed_intents: [small_experiment]
    compatible_verdicts: [good, neutral, caution]
  low_stakes_communication:
    allowed_intents: [communicate_boundary, create_draft]
    compatible_verdicts: [good, neutral, caution]
  pacing:
    allowed_intents: [plan, reduce_load]
    compatible_verdicts: [good, neutral, caution, avoid]
  guardrail:
    allowed_intents: [postpone_major_decision, avoid_escalation, avoid_overcommitment, avoid_all_at_once, avoid_assumption, avoid_extra_intensity]
    compatible_verdicts: [good, neutral, caution, avoid]
```

Forbidden future intent combinations are exact and validated even though the
positive side is not present in v1 templates:

```yaml
forbidden_intent_pairs:
  - [immediate_major_decision, postpone_major_decision]
  - [increase_commitment, avoid_overcommitment]
  - [escalate, avoid_escalation]
  - [replace_everything, avoid_all_at_once]
  - [increase_intensity, avoid_extra_intensity]

forbidden_intents:
  - immediate_major_decision
  - increase_commitment
  - escalate
  - replace_everything
  - increase_intensity
```

The validator must reject a template using a forbidden intent. Do not silently
map it to an allowed one.

### 7.3 Theme sphere ownership

```yaml
theme_spheres:
  communication_learning_documents: [communication, study, documents]
  structure_boundaries_control: [work, money, documents, decisions]
  relationships_values_closeness: [relationships, communication]
  resources_security: [money, documents, decisions, shopping]
  energy_body_pacing: [work, sport, health]
  home_belonging: [money, relationships, decisions]
  inner_clarity_recovery: [health, decisions, creativity]
  direction_growth_meaning: [work, decisions, travel, study]
  creativity_visibility: [work, communication, creativity]
  change_innovation: [work, documents, decisions, creativity]
```

Order in each list is exactly the order shown above. It is semantic template
priority and must remain stable; it is not re-sorted alphabetically or by the
B1 navigator order.

### 7.4 Common template metadata

Unless explicitly marked otherwise below:

```text
tones: [supportive, neutral, tense, mixed]
conditional: false
```

Template `sphere_keys` is the owning theme list from section 7.3 unless a
narrower list is stated. Guidance in B2B2 will use only the intersection with
the selected horizon likely spheres as public provenance.

### 7.5 Exact action matrix — structure and communication

#### `structure_boundaries_control`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `structure.long.inventory` | reflect / reflection | false | Разделите текущие обязательства на свои, совместные и взятые по привычке. |
| long/avoid | `structure.long.no_new_load` | avoid_overcommitment / guardrail | false | Не берите новую долгую ответственность только ради ощущения устойчивости. |
| medium/do | `structure.medium.one_boundary` | communicate_boundary / low_stakes_communication | true | Если сейчас обсуждаются роль, объём работы, деньги или условия договорённости, обозначьте одну конкретную границу. |
| medium/do | `structure.medium.one_system_change` | small_experiment / reversible_experiment | false | Измените один элемент системы и заранее определите, по какому признаку проверите результат. |
| medium/do | `structure.medium.write_ownership` | clarify / reflection | false | Выпишите, что действительно зависит от вас, а что требует отдельной договорённости с другими. |
| medium/avoid | `structure.medium.no_ultimatum` | avoid_escalation / guardrail | false | Не ставьте ультиматум в момент, когда главная потребность — быстро вернуть контроль. |
| medium/avoid | `structure.medium.no_emotional_exit` | postpone_major_decision / guardrail | false | Не принимайте крупное необратимое решение в короткий эмоциональный пик. |
| medium/avoid | `structure.medium.no_control_load` | avoid_overcommitment / guardrail | false | Не берите новую ответственность только для того, чтобы меньше чувствовать неопределённость. |
| fast/do | `structure.fast.fact_principle_reaction` | reflect / reflection | false | Перед ответом отделите факт, принципиальную границу и первую реакцию на давление. |
| fast/avoid | `structure.fast.delay_major` | postpone_major_decision / guardrail | false | Отложите крупное решение до окончания короткого пика. |

#### `communication_learning_documents`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `communication.long.rules` | plan / pacing | false | Определите один устойчивый порядок для важных записей, решений или договорённостей. |
| long/avoid | `communication.long.no_complexity` | avoid_all_at_once / guardrail | false | Не усложняйте всю систему информации из-за одной неясной детали. |
| medium/do | `communication.medium.draft` | create_draft / low_stakes_communication | true | Если готовится важное сообщение или документ, сначала сделайте короткий черновик с одной главной мыслью. |
| medium/do | `communication.medium.one_question` | clarify / reflection | true | Если смысл чужой формулировки неясен, задайте один проверяемый вопрос вместо догадки. |
| medium/avoid | `communication.medium.no_silence_assumption` | avoid_assumption / guardrail | false | Не считайте паузу, короткий ответ или молчание доказательством чужого намерения. |
| fast/do | `communication.fast.reread_phrase` | clarify / reflection | true | Если ответ важен, перечитайте одну ключевую фразу и проверьте, совпадают ли факт и ваш вывод. |
| fast/avoid | `communication.fast.no_hot_send` | avoid_escalation / guardrail | false | Не отправляйте резкий ответ в момент максимального раздражения. |

### 7.6 Exact action matrix — relationships and resources

#### `relationships_values_closeness`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `relationships.long.criteria` | reflect / reflection | false | Сформулируйте, какие признаки взаимности и уважения к границам для вас действительно устойчивы. |
| long/avoid | `relationships.long.no_hidden_test` | avoid_assumption / guardrail | false | Не проверяйте близость скрытыми ожиданиями, о которых другой человек не знает. |
| medium/do | `relationships.medium.one_question` | clarify / reflection | true | Если сейчас есть важный разговор, задайте один прямой вопрос о фактах, ожиданиях или границе. |
| medium/do | `relationships.medium.one_agreement` | communicate_boundary / low_stakes_communication | true | Если договорённость расплывчата, предложите один конкретный следующий шаг, который можно подтвердить или изменить. |
| medium/avoid | `relationships.medium.no_final_conclusion` | postpone_major_decision / guardrail | false | Не делайте окончательный вывод об отношениях по одной реакции или одному дню. |
| fast/do | `relationships.fast.name_need` | clarify / reflection | true | Если тон задел вас сильнее обычного, сначала назовите конкретный факт и то, что требуется уточнить. |
| fast/avoid | `relationships.fast.no_ultimatum` | avoid_escalation / guardrail | false | Не превращайте короткий пик чувствительности в ультиматум. |

#### `resources_security`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `resources.long.criteria` | plan / pacing | false | Определите один понятный критерий достаточного запаса времени, денег или внимания. |
| long/avoid | `resources.long.no_total_rebuild` | avoid_all_at_once / guardrail | false | Не перестраивайте все ресурсные правила одновременно. |
| medium/do | `resources.medium.one_measure` | small_experiment / reversible_experiment | true | Если сейчас пересматривается расход или обязательство, измените один измеримый параметр и проверьте результат. |
| medium/do | `resources.medium.need_vs_relief` | reflect / reflection | true | Если решение хочется принять немедленно, выпишите отдельно реальную необходимость и желание быстро снять неопределённость. |
| medium/avoid | `resources.medium.no_large_emotional` | postpone_major_decision / guardrail | false | Не принимайте крупное финансовое или договорное решение в эмоциональный пик. |
| fast/do | `resources.fast.pause_criteria` | reflect / reflection | true | Если возник импульс потратить, обещать или резко отказаться, сначала вернитесь к заранее выбранному критерию. |
| fast/avoid | `resources.fast.no_impulse` | postpone_major_decision / guardrail | false | Отложите необязательную крупную покупку или новое обязательство до окончания короткого пика. |

### 7.7 Exact action matrix — energy and home

#### `energy_body_pacing`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `energy.long.baseline` | plan / pacing | false | Выберите устойчивый базовый ритм нагрузки, в котором остаётся запас на непредвиденное. |
| long/avoid | `energy.long.no_heroic_norm` | avoid_overcommitment / guardrail | false | Не делайте редкий рывок постоянной нормой нагрузки. |
| medium/do | `energy.medium.one_parameter` | small_experiment / reversible_experiment | false | Измените один параметр нагрузки — объём, темп или паузу — и наблюдайте результат без медицинских выводов. |
| medium/do | `energy.medium.reserve` | plan / pacing | true | Если впереди плотный период, заранее оставьте один свободный интервал вместо полного заполнения графика. |
| medium/avoid | `energy.medium.no_irritation_intensity` | avoid_extra_intensity / guardrail | false | Не увеличивайте интенсивность только из раздражения или желания быстрее доказать результат. |
| fast/do | `energy.fast.reduce_one_step` | reduce_load / pacing | false | Уберите один необязательный источник спешки перед следующим действием. |
| fast/avoid | `energy.fast.no_extra_intensity` | avoid_extra_intensity / guardrail | false | Не добавляйте нагрузку в момент максимального раздражения или спешки. |

#### `home_belonging`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `home.long.conditions` | reflect / reflection | false | Опишите условия пространства и быта, при которых вам легче сохранять устойчивость. |
| long/avoid | `home.long.no_event_assumption` | avoid_assumption / guardrail | false | Не превращайте внутреннюю потребность в опоре в вывод, что обязательно нужен переезд или резкий разрыв привычного порядка. |
| medium/do | `home.medium.one_rule` | small_experiment / reversible_experiment | true | Если сейчас меняется домашний порядок, проверьте одно правило или распределение ответственности в ограниченный срок. |
| medium/do | `home.medium.name_boundary` | communicate_boundary / low_stakes_communication | true | Если личное пространство нарушается, назовите одну конкретную границу без общего обвинения. |
| medium/avoid | `home.medium.no_total_rearrange` | avoid_all_at_once / guardrail | false | Не меняйте весь бытовой порядок из-за одного дня раздражения. |
| fast/do | `home.fast.specific_discomfort` | record_observation / reflection | false | Назовите одно конкретное неудобство, не превращая его в общий вывод о доме или близких. |
| fast/avoid | `home.fast.no_generalization` | avoid_assumption / guardrail | false | Не считайте короткую реакцию доказательством того, что вся ситуация безнадёжна. |

### 7.8 Exact action matrix — inner clarity and direction

#### `inner_clarity_recovery`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `clarity.long.conditions` | reflect / reflection | false | Зафиксируйте условия, после которых ясность обычно возвращается: тишину, порядок входящих или завершённый маленький шаг. |
| long/avoid | `clarity.long.no_diagnosis` | avoid_assumption / guardrail | false | Не превращайте астрологический сигнал или один тяжёлый день в медицинский или психологический диагноз. |
| medium/do | `clarity.medium.one_noise_source` | small_experiment / reversible_experiment | false | Ограничьте один повторяющийся источник информационного шума и заранее выберите срок проверки эффекта. |
| medium/do | `clarity.medium.write_fact_story` | clarify / reflection | false | Выпишите отдельно наблюдаемый факт, свою интерпретацию и то, что пока неизвестно. |
| medium/avoid | `clarity.medium.no_final_in_fatigue` | postpone_major_decision / guardrail | false | Не принимайте окончательное решение только ради прекращения внутреннего шума. |
| fast/do | `clarity.fast.one_fact` | record_observation / reflection | false | Зафиксируйте один факт и вернитесь к выводу после короткой паузы без входящих. |
| fast/avoid | `clarity.fast.no_first_thought` | avoid_assumption / guardrail | false | Не считайте первую громкую мысль самым точным объяснением ситуации. |

#### `direction_growth_meaning`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `direction.long.criteria` | plan / pacing | false | Определите два критерия, по которым долгий путь действительно имеет для вас смысл. |
| long/avoid | `direction.long.no_required_change` | avoid_assumption / guardrail | false | Не считайте, что длительный астрологический цикл сам по себе требует сменить работу, обучение или место жизни. |
| medium/do | `direction.medium.small_test` | small_experiment / reversible_experiment | true | Если появилась новая возможность, проверьте её одним ограниченным шагом без долгого обязательства. |
| medium/do | `direction.medium.success_signal` | plan / pacing | false | Заранее запишите, какой наблюдаемый результат будет признаком, что направление стоит продолжать. |
| medium/avoid | `direction.medium.no_whole_route` | avoid_overcommitment / guardrail | false | Не обещайте себе весь маршрут до результата первого теста. |
| fast/do | `direction.fast.record_idea` | record_observation / reflection | false | Запишите сильную идею и один вопрос, который нужно проверить до решения. |
| fast/avoid | `direction.fast.no_big_commitment` | postpone_major_decision / guardrail | false | Не превращайте короткий подъём ожиданий в крупное обязательство сегодня. |

### 7.9 Exact action matrix — creativity and change

#### `creativity_visibility`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `creativity.long.practice` | plan / pacing | false | Выберите устойчивый способ регулярно доводить идеи до видимого черновика. |
| long/avoid | `creativity.long.no_visibility_rule` | avoid_overcommitment / guardrail | false | Не делайте постоянную публичность обязательным условием ценности результата. |
| medium/do | `creativity.medium.small_audience` | small_experiment / reversible_experiment | true | Если есть черновик, покажите его ограниченной аудитории и запросите один конкретный вид обратной связи. |
| medium/do | `creativity.medium.separate_feedback` | clarify / reflection | false | Разделите фактическую обратную связь, вкусовую реакцию и собственный следующий шаг. |
| medium/avoid | `creativity.medium.no_total_judgment` | avoid_assumption / guardrail | false | Не оценивайте всю свою способность по одной реакции на один результат. |
| fast/do | `creativity.fast.rough_version` | create_draft / low_stakes_communication | false | Сделайте грубую версию следующего шага, не требуя от неё финального качества. |
| fast/avoid | `creativity.fast.no_delete` | postpone_major_decision / guardrail | false | Не удаляйте и не отбрасывайте весь результат в пик реакции на оценку. |

#### `change_innovation`

| horizon/list | id | intent / safety | conditional | exact text |
|---|---|---|---|---|
| long/do | `change.long.outdated_rule` | reflect / reflection | false | Назовите одно правило системы, которое перестало выполнять исходную задачу. |
| long/avoid | `change.long.no_destroy_first` | avoid_all_at_once / guardrail | false | Не разрушайте рабочую систему до появления проверяемой замены. |
| medium/do | `change.medium.one_element` | small_experiment / reversible_experiment | false | Измените один элемент процесса и сравните результат по заранее выбранному критерию. |
| medium/do | `change.medium.rollback` | plan / pacing | false | До эксперимента определите простой способ вернуть прежний вариант, если новый не сработает. |
| medium/avoid | `change.medium.no_everything` | avoid_all_at_once / guardrail | false | Не меняйте одновременно инструмент, сроки, роли и критерий успеха. |
| fast/do | `change.fast.smallest_change` | small_experiment / reversible_experiment | false | Выберите самое маленькое обратимое изменение, которое даст новую информацию. |
| fast/avoid | `change.fast.no_sudden_break` | postpone_major_decision / guardrail | false | Не принимайте решение о резком полном разрыве с прежним способом в короткий пик. |

### 7.10 Action matrix validation

At canon load time prove exact minimum compatible counts for every tone:

```text
long: do >=1, avoid >=1
medium: do >=2, avoid >=1
fast: do >=1, avoid >=1
```

Do not require every template to be compatible with every sphere verdict. That
compatibility is evaluated later against supplied verdicts. However, for each
theme/horizon there must be enough `reflection`, `pacing` or `guardrail`
templates compatible with all verdicts to build a safe fallback at B2B2.

## 8. `personal_patterns.ru.v1.yml` exact rules

### 8.1 Predicate DSL

No arbitrary expressions, Python paths, regex matching of chart data or `eval`.
Support only these discriminated predicates:

```yaml
- type: planet_in_sign
  planet: SATURN
  signs: [CAPRICORN, AQUARIUS, LIBRA]

- type: planet_in_house
  planet: SATURN
  houses: [1, 4, 7, 10]

- type: aspect
  point_a: MERCURY
  point_b: SATURN
  aspect_types: [TRINE, SEXTILE]
  max_orb: 4.0
```

Validation:

- planet/point is one of `SUN MOON MERCURY VENUS MARS JUPITER SATURN URANUS
  NEPTUNE PLUTO`;
- signs are exact 12 uppercase English sign keys;
- houses in `1..12`;
- aspect types from `CONJUNCTION SEXTILE SQUARE TRINE OPPOSITION`;
- `point_a < point_b` in canonical planet order is not required in YAML, but
  loader normalizes for duplicate detection and rejects duplicate equivalent
  predicates/rules;
- `max_orb` finite and `0 < max_orb <= 10`;
- predicates inside one rule are AND;
- lists inside one predicate are OR;
- at least one predicate per rule;
- rules ordered exactly as section 8.3 and IDs globally unique.

### 8.2 Rule schema and confidence

Each rule:

```yaml
id: stable_rule_id
kind: strength|risk
statement_key: existing language key
theme_keys: [one or more]
sphere_keys: [one or more]
base_confidence: 0..1
min_confidence: 0..1
requirements: [typed predicates]
```

Match quality:

```text
planet_in_sign quality = 1.0
planet_in_house quality = 1.0
aspect quality = 1.0 - 0.25 * min(orb / max_orb, 1.0)
rule confidence = round(base_confidence * min(all predicate qualities), 6)
```

Emit only when `confidence >= min_confidence`. Do not tune thresholds at
runtime or based on user identity.

### 8.3 Exact initial pattern catalog

#### Strength rules

```yaml
- id: saturn_angular_dignified_structure
  kind: strength
  statement_key: strength.structure.steady_responsibility
  theme_keys: [structure_boundaries_control, resources_security]
  sphere_keys: [work, money, documents, decisions]
  base_confidence: 0.86
  min_confidence: 0.80
  requirements:
    - {type: planet_in_sign, planet: SATURN, signs: [CAPRICORN, AQUARIUS, LIBRA]}
    - {type: planet_in_house, planet: SATURN, houses: [1, 4, 7, 10]}

- id: mercury_saturn_soft_structured_thinking
  kind: strength
  statement_key: strength.communication.structured_thinking
  theme_keys: [communication_learning_documents, structure_boundaries_control]
  sphere_keys: [work, documents, communication, decisions, study]
  base_confidence: 0.84
  min_confidence: 0.72
  requirements:
    - {type: aspect, point_a: MERCURY, point_b: SATURN, aspect_types: [TRINE, SEXTILE], max_orb: 4.0}

- id: mars_saturn_soft_measured_effort
  kind: strength
  statement_key: strength.energy.measured_effort
  theme_keys: [structure_boundaries_control, energy_body_pacing]
  sphere_keys: [work, sport, health, decisions]
  base_confidence: 0.82
  min_confidence: 0.70
  requirements:
    - {type: aspect, point_a: MARS, point_b: SATURN, aspect_types: [TRINE, SEXTILE], max_orb: 4.0}

- id: mercury_venus_soft_tactful_clarity
  kind: strength
  statement_key: strength.relationships.tactful_clarity
  theme_keys: [communication_learning_documents, relationships_values_closeness]
  sphere_keys: [relationships, communication, documents]
  base_confidence: 0.82
  min_confidence: 0.70
  requirements:
    - {type: aspect, point_a: MERCURY, point_b: VENUS, aspect_types: [TRINE, SEXTILE], max_orb: 4.0}

- id: sun_jupiter_soft_broad_view
  kind: strength
  statement_key: strength.direction.broad_view
  theme_keys: [direction_growth_meaning, creativity_visibility]
  sphere_keys: [work, decisions, travel, creativity, study]
  base_confidence: 0.82
  min_confidence: 0.70
  requirements:
    - {type: aspect, point_a: SUN, point_b: JUPITER, aspect_types: [TRINE, SEXTILE], max_orb: 4.0}

- id: moon_mercury_soft_name_reaction
  kind: strength
  statement_key: strength.inner_clarity.name_reaction
  theme_keys: [communication_learning_documents, inner_clarity_recovery]
  sphere_keys: [health, communication, decisions, creativity]
  base_confidence: 0.80
  min_confidence: 0.68
  requirements:
    - {type: aspect, point_a: MOON, point_b: MERCURY, aspect_types: [TRINE, SEXTILE], max_orb: 4.0}
```

#### Risk rules

```yaml
- id: saturn_pluto_hard_control_under_pressure
  kind: risk
  statement_key: risk.structure.control_under_pressure
  theme_keys: [structure_boundaries_control, resources_security]
  sphere_keys: [work, money, documents, decisions]
  base_confidence: 0.88
  min_confidence: 0.76
  requirements:
    - {type: aspect, point_a: SATURN, point_b: PLUTO, aspect_types: [SQUARE, OPPOSITION], max_orb: 4.0}

- id: mercury_saturn_hard_overchecking
  kind: risk
  statement_key: risk.communication.overchecking
  theme_keys: [communication_learning_documents, structure_boundaries_control]
  sphere_keys: [work, documents, communication, decisions, study]
  base_confidence: 0.84
  min_confidence: 0.72
  requirements:
    - {type: aspect, point_a: MERCURY, point_b: SATURN, aspect_types: [SQUARE, OPPOSITION], max_orb: 4.0}

- id: mars_saturn_hard_increase_pressure
  kind: risk
  statement_key: risk.energy.increase_pressure
  theme_keys: [structure_boundaries_control, energy_body_pacing]
  sphere_keys: [work, sport, health, decisions]
  base_confidence: 0.86
  min_confidence: 0.74
  requirements:
    - {type: aspect, point_a: MARS, point_b: SATURN, aspect_types: [SQUARE, OPPOSITION], max_orb: 4.0}

- id: venus_saturn_hard_defensive_strictness
  kind: risk
  statement_key: risk.relationships.defensive_strictness
  theme_keys: [relationships_values_closeness, resources_security]
  sphere_keys: [money, relationships, communication, decisions]
  base_confidence: 0.84
  min_confidence: 0.72
  requirements:
    - {type: aspect, point_a: VENUS, point_b: SATURN, aspect_types: [SQUARE, OPPOSITION], max_orb: 4.0}

- id: moon_pluto_hard_intensity_before_clarity
  kind: risk
  statement_key: risk.inner_clarity.intensity_before_clarity
  theme_keys: [relationships_values_closeness, structure_boundaries_control, inner_clarity_recovery]
  sphere_keys: [relationships, health, communication, decisions, creativity]
  base_confidence: 0.88
  min_confidence: 0.76
  requirements:
    - {type: aspect, point_a: MOON, point_b: PLUTO, aspect_types: [SQUARE, OPPOSITION], max_orb: 3.0}

- id: sun_uranus_hard_all_at_once
  kind: risk
  statement_key: risk.change.all_at_once
  theme_keys: [direction_growth_meaning, creativity_visibility, change_innovation]
  sphere_keys: [work, documents, decisions, creativity]
  base_confidence: 0.84
  min_confidence: 0.72
  requirements:
    - {type: aspect, point_a: SUN, point_b: URANUS, aspect_types: [SQUARE, OPPOSITION], max_orb: 4.0}
```

`dominants`, `top_signals` and generic planet prominence must not be used as an
implicit alternative when a rule does not match.

## 9. Internal PersonalFactPack schema

Create `apps/api/app/schemas/personal_fact_pack.py` using internal frozen
`BaseModel`, not public `CamelModel`.

### 9.1 Exact models

```py
PersonalFactKind = Literal["strength", "risk", "profile", "natal", "sphere"]

class PersonalFact(BaseModel):
    id: str
    kind: PersonalFactKind
    statement_key: str
    confidence: float
    horizon_ids: tuple[TodayV2HorizonId, ...]
    theme_keys: tuple[str, ...]
    activation_ids: tuple[str, ...]
    natal_source_ids: tuple[str, ...]
    profile_source_ids: tuple[str, ...]
    sphere_keys: tuple[TodayV2ProductSphereKey, ...]

class PersonalFactPack(BaseModel):
    schema_version: Literal["personal-fact-pack.v1"]
    selected_activation_ids: tuple[str, str, str]
    facts: tuple[PersonalFact, ...]
```

`ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)` for both.

### 9.2 Fact validation

All facts:

- ID pattern `^[a-z0-9][a-z0-9._:-]{2,127}$`;
- statement key pattern `^[a-z0-9][a-z0-9._-]{2,127}$`;
- finite confidence in `0..1`, already rounded to 6 decimals;
- horizon IDs are a non-empty canonical subsequence of long/medium/fast;
- theme/activation/source/sphere tuples unique and canonical/deterministic;
- activation IDs subset `selected_activation_ids`;
- at least one of activation/natal/profile/sphere sources non-empty;
- no field stores user-facing statement text.

Kind-specific invariants:

```text
strength/risk:
  natal_source_ids non-empty
  activation_ids non-empty
  theme_keys non-empty
  sphere_keys non-empty

sphere:
  exactly one horizon_id
  exactly one activation_id
  exactly one sphere_key
  natal_source_ids/profile_source_ids empty

profile:
  profile_source_ids non-empty

natal:
  natal_source_ids non-empty
```

B2B1 emits only `sphere`, `strength`, and `risk`; other kinds remain typed for
future reviewed sources. No placeholder profile/natal fact is emitted merely to
fill the enum.

Pack validation:

- selected activation order corresponds exactly to long, medium, fast input;
- selected IDs unique;
- fact IDs globally unique;
- every fact activation subset selected IDs;
- facts ordered: all sphere facts in horizon/product-sphere order, then matched
  personal rules in canon order;
- repeated construction serializes byte-identically.

### 9.3 Stable IDs

Exact ID formats:

```text
sphere fact: pf:v1:sphere:<horizon>:<product_sphere>
personal rule fact: pf:v1:<strength|risk>:<rule_id>
```

Do not append sign, house, aspect, orb, date, timezone, username, hash of raw
data or activation human evidence.

Generic natal source IDs:

```text
planet_in_sign  -> natal:planet:<lower_planet>
planet_in_house -> natal:house:<lower_planet>
aspect          -> natal:aspect:<lower_canonical_point_a>:<lower_canonical_point_b>
```

If two requirements produce the same generic source ID, keep one in first-rule
order.

## 10. PersonalFactPackService

Create `apps/api/app/services/personal_fact_pack_service.py` with one public
entrypoint:

```py
class PersonalFactPackService:
    def build(
        self,
        *,
        selection: SelectedHorizonTriple,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
        natal_context: NatalContextData,
    ) -> PersonalFactPack:
        ...
```

No profile ORM/schema argument in B2B1.

### 10.1 Input integrity

Before extraction:

1. build activation map and reject duplicate activation IDs;
2. selected IDs must exist, be active and equal ordered long/medium/fast IDs;
3. selected evidence technique/family/target identity must equal anchor data
   after the same B2A normalization rules;
4. selected timing boundaries must still equal evidence timing;
5. scoring numeric fields/contribution amounts used here must be finite;
6. normalized natal planet names must be unique;
7. natal aspect orb must be finite and non-negative;
8. invalid internal state raises compact `ValueError`/dedicated internal error
   with structural path and stable ID only, never raw human text/value.

Do not catch programming/integrity errors and return an empty pack.

### 10.2 Sphere facts

For each selected anchor in long/medium/fast order:

1. inspect only scoring spheres named by `anchor.technical_spheres`;
2. select contributions where `source == "activation"` and
   `source_id == anchor.activation_id`;
3. require at least one finite non-zero linked contribution; otherwise raise
   `selected-anchor-without-scoring-contribution`;
4. for each `anchor.product_spheres` in existing order emit one sphere fact;
5. fact confidence is exactly `anchor.impact_score`;
6. fact `statement_key` is `sphere.active.<product_sphere>`;
7. language canon must contain all 12 `sphere.active.*` statement keys as
   machine labels, not user prose.

Add to language canon exact sphere fact statement keys with kind `sphere` and
text equal the corresponding product-sphere `label`. This text is not emitted
by the fact pack and exists for B2B2 lookup/validation.

Sphere fact fields:

```text
horizon_ids: current horizon only
theme_keys: anchor.theme_keys
activation_ids: current anchor only
natal/profile source ids: empty
sphere_keys: current product sphere only
```

### 10.3 Natal normalization/matching

Normalization for comparison only:

- strip repeated `Transit_`/`Natal_` prefixes case-insensitively;
- trim and uppercase planet/sign/aspect keys;
- aspect point order is canonical known-planet order;
- wire/cache values remain untouched.

For each personal pattern in canon order:

1. find all selected anchors where both intersections are non-empty:

```text
anchor.theme_keys ∩ rule.theme_keys
anchor.product_spheres ∩ rule.sphere_keys
```

2. if no linked anchor, skip without evaluating into a claim;
3. evaluate all predicates against exact natal data;
4. for multiple matching aspects select smallest orb, then canonical point pair,
   then normalized aspect type;
5. compute confidence by section 8.2;
6. if below threshold, omit;
7. emit one fact for the rule, not one per horizon;
8. linked horizon/activation IDs use long/medium/fast selection order;
9. fact theme/sphere keys are the stable ordered intersections actually linked
   to selected anchors, not every rule key blindly;
10. natal source IDs come only from matched predicates.

Do not use:

```text
natal_context.dominants
natal_context.top_signals
natal_context.sphere_scores
natal_context.elements_balance
natal_context.modalities_balance
natal_context.special_points
longitude/degree
```

### 10.4 Privacy proof

The service must never place the following sentinel inputs in
`model_dump_json()` or exception messages:

```text
PERSON_NAME_SENTINEL
PRIVATE_CITY_SENTINEL
RAW_ACTIVATION_EVIDENCE_SENTINEL
RAW_ACTIVATION_DEBUG_SENTINEL
RAW_SCORING_DEBUG_SENTINEL
AQUARIUS
HOUSE_10_SENTINEL
OPPOSITION
ORB_1_05_SENTINEL
```

Planet names in generic source IDs are allowed; matched sign/house/aspect/orb
are not.

## 11. Internal horizon tone schema

Create `apps/api/app/schemas/horizon_tone.py`.

Exact internal model:

```py
HorizonSphereVerdict = Literal["good", "neutral", "caution", "avoid"]

class HorizonToneAssessment(BaseModel):
    horizon: TodayV2HorizonId
    tone: TodayV2HorizonTone
    activation_confidence: float
    activation_component: float
    sphere_component: float
    net_score: float
    opposing_material_evidence: bool
    activation_ids: tuple[str, ...]
    sphere_keys: tuple[TodayV2ProductSphereKey, ...]

class HorizonToneResult(BaseModel):
    schema_version: Literal["horizon-tone.v1"]
    items: tuple[HorizonToneAssessment, HorizonToneAssessment, HorizonToneAssessment]
```

Frozen/forbid/hide input. All numeric values finite, in `-1..1` where signed,
`0..1` for confidence, six-decimal rounded. Items exactly long/medium/fast.

## 12. HorizonToneService algorithm

Create `apps/api/app/services/horizon_tone_service.py`:

```py
class HorizonToneService:
    def assess(
        self,
        *,
        selection: SelectedHorizonTriple,
        sphere_verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
    ) -> HorizonToneResult:
        ...
```

Do not accept/inspect `ConcreteAdviceRow.text`, Russian labels or CSS status.

For each anchor:

```text
activation_confidence = round6(
    strength_feature     * 0.35 +
    contribution_feature * 0.25 +
    convergence_feature  * 0.15 +
    impact_score         * 0.25
)
```

Weights come from canon, not literals.

Polarity numeric value:

```text
supportive -> +1
neutral    ->  0
tense      -> -1
mixed      -> special explicit-mixed path
```

```text
activation_component = round6(polarity_value * activation_confidence)
```

Sphere component:

- consider only supplied verdicts whose keys are in anchor product spheres;
- preserve anchor product-sphere order;
- missing verdict keys are ignored and contribute no guessed value;
- if none available, component is `0.0`;
- otherwise arithmetic mean of canon verdict values, round6.

```text
net_score = round6(
    activation_component * activation_weight +
    sphere_component * sphere_verdict_weight
)
```

Opposing material evidence is true iff:

```text
activation_component and sphere_component have opposite non-zero signs
AND abs(activation_component) >= mixed_opposing_min
AND abs(sphere_component) >= mixed_opposing_min
```

Tone decision order is exact:

1. anchor polarity `mixed` -> `mixed`;
2. opposing material evidence -> `mixed`;
3. net score `>= supportive_min` -> `supportive`;
4. net score `<= tense_max` -> `tense`;
5. otherwise -> `neutral`.

Assessment provenance:

```text
activation_ids: exactly current anchor activation ID
sphere_keys: only supplied verdict keys used for sphere_component
```

Input mapping with unknown sphere key or unknown verdict must fail; duplicate is
impossible in mapping. Reversed mapping insertion order must not change output.

## 13. Canon startup integration

Update `apps/api/app/services/canon_service.py` minimally:

- add the three files to `OPTIONAL_INTERNAL_CANON_FILES` only so existing raw
  bundle readers can see them without changing core `CANON_FILES` identity;
- inside `validate_canon_bundle(canon_dir)` call
  `load_horizon_content_canons(canon_dir.resolve())` after existing B2A loader;
- invalid/missing B2B1 canon therefore fails API import/startup;
- keep `CANON_VERSIONS` and `get_canon_versions()` byte-equivalent;
- do not make `load_canon_bundle()` the runtime source for B2B services;
- no circular import at module import time.

`test_canon_service.py` must prove a copied valid full canon directory succeeds
and omission/corruption of each new file fails strict validation.

## 14. Testkit

Create `apps/api/tests/_horizon_content_testkit.py` with GRACE and only synthetic
builders. It may reuse B2A `_horizon_selection_testkit` builders but must not
modify that accepted file.

Required builders:

```text
build_selected_story(theme)
build_natal_context(planets/aspects overrides)
build_structure_natal()
build_communication_natal()
build_relationship_natal()
build_sphere_verdicts(...)
build_fact_pack(...)
```

All dates/people/locations synthetic. No DB, real user ID, frontend fixture,
network or clock.

## 15. Focused canon tests

Create `test_horizon_content_canon_service.py`. Minimum matrix:

### Load/version/cache

- real default bundle loads;
- version helper exact three-key map;
- repeated default load returns cached object identity;
- explicit directories isolated by resolved path;
- cache clear resets both caches;
- cwd independence;
- missing each file fails;
- malformed each file fails;
- error hides raw YAML copy/value.

### Strict schema

- extra key at every major level fails;
- wrong schema/version/locale fails;
- missing/extra technique/theme/sphere/tone/state/horizon key fails;
- duplicate/blank action ID/text fails;
- unknown placeholder fails;
- invalid tone weights/sums/thresholds/non-finite values fail;
- unknown safety/intent/verdict fails;
- forbidden intent in template fails;
- conditional true without allowed prefix fails;
- modifying any exact reviewed action into a forbidden certainty/high-stakes
  phrase fails;
- action count coverage fails when one required template removed;
- action sphere outside/without owning theme intersection fails;
- unknown/duplicate natal predicate fails;
- invalid planet/sign/house/aspect/orb/confidence fails;
- missing/mismatched personal or sphere-fact statement fails;
- unreferenced/duplicate-referenced v1 statement fails;
- normalized equivalent aspect predicates/rules fail as duplicate.

Tests must mutate one independent field at a time and assert structural failure,
not one broad `raises` test.

## 16. Personal fact pack tests

Create `test_personal_fact_pack_service.py`.

### 16.1 Golden fact packs

1. Structure natal:

```text
Saturn Aquarius house 10
Saturn square Pluto orb 1.0
selected theme structure_boundaries_control
```

Expected:

```text
strength.structure.steady_responsibility
risk.structure.control_under_pressure
plus selected sphere facts
```

2. Communication natal:

```text
Mercury trine Saturn orb 1.5
selected theme communication_learning_documents
```

Expected structured-thinking strength, no structure risk.

3. Relationship natal:

```text
Mercury sextile Venus orb 1.0
Venus opposition Saturn orb 2.0
selected theme relationships_values_closeness
```

Expected tactful-clarity strength + defensive-strictness risk.

Assert the three serialized packs and statement-key sets are materially
different.

### 16.2 Match/link boundaries

- missing one AND predicate -> no rule fact;
- aspect type mismatch -> no rule fact;
- orb exactly max -> confidence formula and threshold behavior exact;
- orb just above max -> no match;
- confidence exactly min -> emit;
- one 1e-6 below min -> omit;
- chart match but no selected theme intersection -> omit;
- theme match but no selected sphere intersection -> omit;
- generic `dominants=["Saturn","Pluto"]` only -> no strength/risk;
- `top_signals`/natal sphere score sentinel only -> no strength/risk;
- reverse natal aspect point order -> identical pack;
- reverse natal aspect list/selection input supporting collections -> identical
  serialization;
- multiple matching aspects chooses smallest orb deterministically;
- malformed negative/non-finite orb fails structurally.

### 16.3 Sphere/scoring integrity

- one sphere fact per selected anchor product sphere;
- only activation-linked contribution accepted;
- unrelated/base/convergence contribution cannot ground it;
- missing selected contribution raises;
- inactive/missing/duplicate selected activation raises;
- selection/evidence identity or timing mismatch raises;
- fact activation IDs subset selected IDs;
- exact stable ID formats;
- six-decimal confidence.

### 16.4 Privacy/determinism

- sentinel packet from section 10.4 absent from serialized pack/errors;
- no statement body in fact pack;
- no raw sign/house/aspect/orb;
- two identical builds byte-identical;
- all internal schema impossible states rejected;
- fact/source/activation IDs stable under unrelated natal/scoring debug changes.

## 17. Tone tests

Create `test_horizon_tone_service.py`.

Minimum isolated matrix:

- supportive polarity + no sphere verdict -> supportive above boundary;
- tense polarity + no sphere verdict -> tense below boundary;
- neutral polarity + good verdict only remains neutral under exact weights;
- explicit mixed polarity always mixed;
- supportive activation + material caution/avoid sphere -> mixed;
- tense activation + material good sphere -> mixed;
- opposing sphere evidence below `mixed_opposing_min` does not force mixed;
- net exactly supportive threshold -> supportive;
- one 1e-6 below -> neutral;
- net exactly tense threshold -> tense;
- one 1e-6 above -> neutral;
- missing verdicts ignored, not treated as neutral rows in denominator;
- only anchor product-sphere verdicts used;
- reversed mapping insertion order byte-identical;
- unknown sphere/verdict rejected;
- feature weights individually influence result (mutation-sensitive tests);
- contribution and convergence are genuinely consumed, not dead config;
- all output order/provenance/numeric invariants;
- labels are not inspected and changing Russian copy cannot change tone.

Use explicit-path copied canon mutations for numeric boundary tests. Restore
cache isolation after every test.

## 18. Static and regression gates

Coder must run before callback:

```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_content_canon_service.py \
  tests/test_personal_fact_pack_service.py \
  tests/test_horizon_tone_service.py -q

cd /opt/solarsage-astro
pnpm contracts:check
git diff --check

cd apps/api
.venv/bin/python -m pytest tests -q
```

Full API expectation for this wave is exact accepted B2A baseline only:

```text
6 failed, 937 passed, 5 skipped
```

The six failure node IDs must equal exactly:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

Any new/different failure is a blocker. Do not fix baseline failures in B2B1.

Contracts gate must show no generated/public diff. Also run:

```bash
git diff --name-only
git diff -- apps/api/app/schemas/today.py apps/api/app/schemas/today_horizons.py
git diff -- packages apps/web openapi contracts/generated
```

Expected second/third diffs: empty.

## 19. Maintainability limits

- no Python module over 650 lines without returning to architect;
- no test module over 700 lines; split by concern if needed;
- no one-line compressed tests/copy dictionaries;
- YAML may be long because copy is data, but preserve readable one-template-per
  block formatting;
- no duplicated canon constants in service code;
- no generic recursive validation framework; explicit typed models are preferred;
- no regex-based Russian prose generation.

## 20. Final callback — no commit/push

Return exactly this shape in tmux:

```text
READY_STAGE_B2B1_FACTS_TONE_REVIEW
branch: preview/solarsage-v2-human-first-navigator-ux
base_head: cd27d1a8056eef92737e992c1b0998423331734b
changed_paths: <exact list>
canon_files: PASS
cross_canon_validation: PASS
fact_pack_goldens: PASS <three fact key summaries>
unlinked_or_weak_claims: OMITTED
privacy_sentinels: ZERO
tone_matrix: PASS
focused_tests: <count passed>
contracts_check: PASS_NO_PUBLIC_DIFF
api_full: <exact result and failure IDs>
git_diff_check: PASS
public_population: NONE
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
```

Do not proceed into B2B2. Stop and wait for architect review.
