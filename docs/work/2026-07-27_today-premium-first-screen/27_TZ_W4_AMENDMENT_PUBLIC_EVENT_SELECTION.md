# W4 Amendment A1: канон public events и единый источник «Что сошлось сегодня»

Дата: 2026-07-28  
Phase / Wave: **W4-TODAY-CONVERGENCE**, amendment A1 / будущий срез B2.1  
Родитель:
`docs/work/2026-07-27_today-premium-first-screen/21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md`  
Уточняет:
`24_TZ_W4_B2_FOCUS_ASSEMBLY.md`,
`25_TZ_W4_C1_FOCUS_SCHEMA.md`,
`26_TZ_W4_C2_FOCUS_NARRATIVE.md`  
Modules: `M-TODAY-FOCUS-BUILDER`, `M-TODAY-SERVICE`, day audit contract,
frontend Today composition  
Статус: **normative amendment**. Ничего не коммитить и не пушить — коммит
делает ревьюер.

Следующие операционные документы являются обязательными продолжениями этого
amendment: `28_TZ_W4_F1_TODAY_FOCUS_FRONTEND_MIGRATION.md`,
`29_TZ_W4_O1_PREGEN_CACHE_RELIABILITY.md` и
`30_TZ_W4_CANARY_SANITIZED_FIXTURES.md`.

## 0. Приоритет amendment и влияние на текущий C2

Этот документ:

1. **Не останавливает и не расширяет текущий W4-C2.** Кодер C2 продолжает
   deterministic human titles, один structured LLM core-вызов и строгий
   `contentState` по `26_TZ_W4_C2_FOCUS_NARRATIVE.md`.
2. Создаёт следующий отдельный backend-срез **W4-B2.1** для изменения отбора
   public events после завершения/review C2.
3. Переопределяет только следующие старые положения:
   - B2 §2 «Events: из выбранной группы/импульсов»;
   - родитель §4.4 в той части, где ranking групп неявно определяет весь
     список public events.
4. Не меняет grouping и ranking победившего convergence, расчёт valence,
   `dayStatus`, `relativeStatus`, featured-sphere ranking и LLM ownership.

Если этот amendment расходится с указанными положениями родителя/B2, для
public event selection действует этот документ.

### 0.1. Entry gate для B2.1

B2.1 начинается только после того, как C2 получил отдельный clean commit и
review evidence по `26_TZ_W4_C2_FOCUS_NARRATIVE.md`. Незакоммиченные изменения
текущего кодера не являются доказательством готовности C2. До старта B2.1
ревьюер фиксирует:

1. prompt/schema и `contentState` C2 приняты;
2. deterministic title builder возвращает `None`/явный reject для
   непубликуемого machine-key фактора, а не шаблонный fallback;
3. normalized integration fixture действительно содержит поля, нужные
   title builder (`aspect_type`, `target_type` и human-label mapping);
4. B2 group winner и canonical valence reducer либо совпадают, либо открыто
   зафиксировано отдельное решение владельца. B2.1 не маскирует расхождение
   reducer-ов.

Frontend F1 может готовить адаптер параллельно, но production canary не
разрешается до прохождения также O1 и sanitized-fixture gates из документов
28–30.

---

## 1. Проблема, доказанная live audit 2026-07-28

Текущая реализация сначала ранжирует convergence-группы, затем заполняет
`focus.events` якорями в порядке групп. Из-за этого рейтинг сюжета подменяет
рейтинг отдельных событий.

На обезличенном live-кейсе 28.07.2026, Europe/Moscow, public cap выбрал:

```text
00:18 — Moon sextile natal Mercury       supportive, strength 0.0137
00:35 — Moon quincunx Lot Necessity      neutral,    strength 0.1144
13:31 — Moon square natal Pluto          tense,      strength 0.7200
```

При этом из public output был вытеснен рассчитанный точный импульс:

```text
19:52 — Mars opposition natal Neptune    tense,      strength 0.9076
```

Это детерминированно объясняется текущим кодом, но нарушает продуктовую цель:
пользователь видит слабое или нейтральное событие вместо одного из сильнейших
точных событий дня.

### 1.1. Корневой вывод

Нужны два независимых backend-owned решения:

1. **Какой сюжет победил** — существующий convergence group ranking.
2. **Какие три реальные точки дня показать** — отдельный public event
   selection после выбора сюжета.

LLM не участвует ни в одном решении.

---

## 2. Продуктовый канон Today

### 2.1. Единственный source of truth

Для пользовательского блока «Что сошлось именно сегодня» единственным
source of truth является корневое поле `focus` (`TodayFocus`).

Запрещено использовать как альтернативный headline/сюжет этого блока:

- `v2.activationSummary.headline`;
- legacy `v2.whyToday`;
- legacy `whyThisHappens`;
- `headline`, `reading`, `notes` старого Today;
- самостоятельно выбранную фронтендом планету/сферу.

Legacy-поля пока сохраняются в API для совместимости, аудита и controlled
migration. Их удаление — отдельная задача после consumer audit. Они не должны
конкурировать с `focus` в новом UI.

### 2.2. Разделение ответственности

- `dayStatus` / valence отвечает: **каков общий тон дня**.
- `relativeStatus` отвечает: **насколько день отличается от личного фона**.
- `focus` отвечает: **что получило реальный временной импульс именно сегодня**.
- полный список 12 сфер остаётся ниже и не превращается в 12 независимых
  «схождений».

`focus` не пересчитывает и не объясняет формулу `dayStatus`. Focus narrative
не должен объявлять весь день «тяжёлым», «лёгким» или «лучшим», если это не
является отдельным validated input из valence-композиции.

### 2.3. Годовые и медленные техники

Фирдар, профекция, return, solar arc и другой длительный фактор:

- не становится событием дня только потому, что активен весь период;
- не получает ежедневную строку с временем без реального ingress/peak;
- может войти в evidence выбранного convergence только после появления
  `anchor_today` и только при строгой связи с его target/theme+sphere;
- формулируется как «контекст периода», а не как новое событие сегодня.

Таким образом, годовая техника не показывается каждый день. Она появляется в
объяснении лишь тогда, когда быстрый сегодняшний якорь попал в ту же тему.

### 2.4. Полный расчёт не равен публичной выдаче

Нормализация, ledger, valence и агрегация всего набора факторов сохраняются.
Они нужны для dayStatus, relativeStatus, winner convergence, evidence,
featured spheres, 12 сфер и audit provenance. Три public events — финальная
проекция полного расчёта, а не замена расчёта тремя входами.

B2.1 запрещено «оптимизировать» через раннее удаление 147 факторов до
grouping/valence. Оптимизация latency в O1 касается LLM orchestration/cache,
поскольку sidecar+deterministic aggregation на измеренном кейсе занимали менее
секунды и не объясняли 75-секундный хвост.

---

## 3. Нормативный public event selection

### 3.1. Candidate pool

До отбора выполнить canonical physical dedup. Кандидатом public event может
быть только фактор, который одновременно:

1. имеет `temporal_role="anchor_today"` для локальной даты пользователя;
2. имеет допустимый `kind`: `exact|starts|peak|building|separating`;
3. для `exact|starts|peak` действительно принадлежит интервалу локального дня
   `[00:00, 24:00)` в IANA timezone пользователя;
4. имеет traceable provenance (`source_activation_ids` либо canonical ledger
   factor id);
5. проходит deterministic public-title eligibility: никаких `NECESSITY`,
   `Transit_`, `Natal_` и других machine keys в `human_title`;
6. не является semantic/physical дублем уже выбранного события.

Если human title нельзя построить честно, фактор пропускается, а селектор
пытается взять следующего кандидата. LLM не исправляет и не маскирует
невалидный deterministic title.

### 3.1.1. Identity и provenance public event

В текущем wire-контракте идентичность не смешивается с provenance:

```text
event.id                  = ev:<canonical_factor_id>
event.sourceActivationIds = [<canonical_activation_id>, ...]
```

Для activation-backed factor `canonical_factor_id` имеет вид
`act:<canonical_activation_id>`. Поэтому для canary 28.07 это, например,
`ev:act:t2n__MOON__SQUARE__PLUTO` и
`sourceActivationIds: ["t2n__MOON__SQUARE__PLUTO"]`. Если реализация имеет
другой уже опубликованный stable-id формат, сохраняется именно текущий wire
формат; менять схему ради canary запрещено. В тестах и UI `event.id` используется
для публичной строки, а `sourceActivationIds` — для трассировки к ledger.

Title eligibility проверяется на том же normalized `TodayFactor`, который
передан селектору. Нельзя сначала отобрать factor, а затем подменить его
machine-key текстом в адаптере или LLM.

### 3.2. Обязательный якорь convergence

Для `state="convergence_today"` в selected set резервируется одно место под
primary `anchor_today` победившей convergence-группы.

- Если primary anchor не public-eligible, взять следующий eligible anchor той
  же победившей группы по её детерминированному порядку.
- Если eligible anchor в группе отсутствует, `state` и convergence facts не
  переписываются, но событие не публикуется; случай логируется/тестируется как
  contract anomaly.
- Supporting/background factor не может занять это зарезервированное место.

Для `state="single_impulses"` зарезервированного convergence-якоря нет.

### 3.3. Заполнение оставшихся мест

После обязательного якоря оставшиеся кандидаты со **всех** дневных групп и
single impulses ранжируются лексикографически:

1. timing precision: `exact_today` → `starts_today` → `delta_peak`;
2. valenced factor (`supportive|tense|mixed`) выше `neutral`;
3. выше нормализованный canonical `strength`;
4. раньше `occurs_at`;
5. stable `factor_id` как последний tie-break.

Берутся первые кандидаты до общего cap `3`.

`strength` обязан быть canonical snapshot выбранной даты, а не значением,
зависящим от wall-clock момента HTTP-запроса. Повторные запросы одной даты до
и после конкретного события не должны менять selected set при той же версии
расчёта и входных данных.

`occurs_at` может быть `null` у допустимого delta/границы без точного времени.
Такой фактор не получает выдуманные часы: он участвует в selection priority,
но при display sort уходит после всех timed events.

Запрещено:

- повторно ранжировать оставшиеся события по позиции их convergence-группы;
- вводить LLM relevance score;
- принудительно добавлять «позитивное» событие для баланса;
- вытеснять сильный ненейтральный exact factor более слабым neutral factor
  только потому, что neutral factor относится к более богатой группе.

### 3.4. Selection order и display order — разные вещи

Selection priority определяет **состав** множества из 0–3 событий. После
выбора public API сохраняет существующий display contract:

```text
events.sort((occurs_at is null) ASC, (occurs_at or MAX_INSTANT) ASC, id ASC)
```

То есть обязательный convergence anchor не обязан визуально быть первой
строкой, если другое выбранное событие случилось раньше. Связь anchor с
convergence хранится через IDs/provenance, а не через позицию строки.

Нормативный null-safe comparator:

```text
(occurs_at is null) ASC, (occurs_at или MAX_INSTANT) ASC, event.id ASC
```

Все instant сначала переводятся в timezone пользователя только для показа;
сравнение фактов остаётся по canonical instant. `null` всегда последняя группа,
затем stable `event.id`.

### 3.5. Связь selected events с победившим convergence

Публичный список смешивает convergence anchor и независимые сильные события,
но narrative не должен смешивать их evidence. Для каждого selected event
детерминированно вычислить:

```text
convergenceEventIds = {
  event.id
  | intersect(event.sourceActivationIds,
              winning_convergence.sourceActivationIds) != ∅
}
independentEventIds = selectedEventIds - convergenceEventIds
```

В `convergence_today` обязательный anchor обязан входить в
`convergenceEventIds`; остальные выбранные строки обычно находятся в
`independentEventIds`. В LLM evidence pack передаются обе секции с явными
ролями. Summary/convergence claims могут ссылаться только на первую секцию;
independent events получают отдельные meanings и не объявляются частью
схождения. Это внутреннее partitioning, не повод менять wire schema.

### 3.6. Состояния

- `convergence_today`: обязательный eligible anchor победившей группы + до
  двух лучших независимых событий всего дня.
- `single_impulses`: до трёх лучших независимых событий всего дня по §3.3,
  без заявления «сошлось».
- `background_only|no_accent`: `events=[]`.
- `unavailable`: factual calculation unavailable; не смешивать с
  `contentState="unavailable"`.

---

## 4. Нормативный результат canary 2026-07-28

Для обезличенного normalized ledger владельца, дата 2026-07-28,
Europe/Moscow, selected set обязан содержать:

```text
event.id: ev:act:t2n__MOON__SQUARE__PLUTO
event.id: ev:act:t2n__MOON__SEXTILE__URANUS
event.id: ev:act:t2n__MARS__OPPOSITION__NEPTUNE

sourceActivationIds:
  t2n__MOON__SQUARE__PLUTO
  t2n__MOON__SEXTILE__URANUS
  t2n__MARS__OPPOSITION__NEPTUNE
```

Display order и ожидаемая человеческая форма:

```text
13:31 — Луна в напряжении с твоим Плутоном
18:19 — Луна в гармонии с твоим Ураном
19:52 — Марс напротив твоего Нептуна
```

Почему именно этот набор:

1. Moon–Pluto — обязательный exact anchor победившего Pluto convergence.
2. Mars–Neptune — strongest remaining valenced exact event (`0.9076`).
3. Moon–Uranus — следующий remaining valenced exact event (`0.2005`).

В canary ожидается `relation=convergence_event` только у Moon–Pluto;
Mars–Neptune и Moon–Uranus имеют `relation=independent_event` даже если
frontend визуально показывает их в одной карточке. Фактическое поле relation
не добавляется в wire без отдельного schema decision: до этого оно выводится
из provenance partition по §3.5.

Нейтральный Moon–Lot Necessity и уже слабый к моменту расчёта Moon–Mercury не
проходят cap. В fixture запрещено сохранять birth data, Telegram ID/username
или raw profile; только обезличенные normalized factors.

---

## 5. LLM и `contentState`

W4-C2 получает только уже выбранный backend-набор public events. LLM:

- не добавляет и не удаляет событие;
- не меняет порядок, время, kind, title, target, IDs и spheres;
- не упоминает событие, отсутствующее во входном evidence pack;
- получает convergence и independent evidence раздельно по §3.5;
- не форматирует UTC через `strftime("%H:%M")` и не владеет timezone
  conversion: часы для UI вычисляет deterministic boundary;
- пишет `convergence.summary`, `event.meaning`, sphere `summary/action`;
- проходит атомарную schema/claim validation.

После завершения C2 действует таблица:

| `focus.state` | Допустимый `contentState` |
|---|---|
| `convergence_today` | `ready|pending|unavailable` |
| `single_impulses` | `ready|pending|unavailable` |
| `background_only` | `not_needed` |
| `no_accent` | `not_needed` |
| `unavailable` | `unavailable` |

Для `convergence_today|single_impulses` значение `not_needed` после rollout
C2 является ошибкой интеграции. Наличие валидного legacy headline/reading не
может превратить focus `unavailable` в `ready`.

Таблица является producer/cache invariant, а не рекомендацией. O1 добавляет
schema-level validator и negative tests для невозможных пар, включая
`convergence_today + not_needed` и `background_only + ready`. До этого ни
fixture, ни unit test не должны легализовать такую комбинацию.

При timeout/невалидном ответе сохраняются factual events и время, все
LLM-owned поля равны `null`, UI честно показывает:

```text
Персональный разбор пока не готов
```

Никакого fallback-копирайтинга.

---

## 6. Exact implementation scope W4-B2.1

### 6.1. Backend

- Начинать только после entry gate §0.1; в B2.1 diff не включать незавершённые
  C2/F1 изменения текущего кодера.
- `apps/api/app/services/today_focus_builder.py`
  - отделить convergence group ranking от public event selection;
  - реализовать §3 как pure deterministic block/function;
  - сохранить display sorting после selection;
  - сохранить GRACE contracts/maps и актуализировать `owned_tests`.
- `apps/api/tests/test_today_focus_builder.py`
  - добавить boundary/permutation/canary tests §8.
- при необходимости использовать deterministic eligibility из
  `apps/api/app/services/focus_title_builder.py`; не дублировать словари
  human labels и не создавать dependency cycle.

До merge приложить отдельный маленький audit результата B2 ranking: если
family-group reducer и canonical valence reducer расходятся на границе рангов,
селектор не «чинит» это локальным коэффициентом. Нужен либо единый reducer,
либо явное решение владельца с отдельным TZ.

### 6.2. Audit visibility

- `scripts/audit_day_contract.py`
  - печатать `focus.state`, `focus.contentState`, convergence theme/count;
  - печатать selected public events: local time, stable id, kind;
  - проверять cap, local-date/timezone и существование source IDs;
  - не печатать raw profile, birth data, Telegram credentials и LLM evidence.

### 6.3. Cache/versioning

Вопросы cache identity, bounded deadline, pregen retry и rollout вынесены в
отдельный обязательный срез
`29_TZ_W4_O1_PREGEN_CACHE_RELIABILITY.md`. B2.1 не должен в своём diff
одновременно менять `day_service.py`/provider chain и селектор: это сделает
невозможным доказать, что изменился именно public event set.

При rollout нового selector:

- увеличить текущий `TODAY_CONTENT_VERSION`, потому что тот же day/profile
  должен получить новый canonical event set;
- `Payload/OpenAPI` version не увеличивать, если wire schema не меняется;
- `Prompt version` увеличивать только при изменении prompt/schema;
- не считать старый cache current и не удалять его — точный rollout/runbook
  находится в O1.

### 6.4. Frontend / design handoff

Полный migration contract находится в
`28_TZ_W4_F1_TODAY_FOCUS_FRONTEND_MIGRATION.md`; этот раздел фиксирует только
семантические границы backend handoff.

В отдельном frontend/design срезе:

- блок «Что сошлось именно сегодня» читает только `focus`;
- показывает 0–3 backend-sorted events; локальное время получает только из
  canonical `occursAt` + backend-provided IANA `timezone`;
- показывает 0–3 `featuredSpheres`, затем полный список 12 сфер отдельно;
- frontend не пересортировывает events по тексту, силе или CSS-позиции;
- legacy `activationSummary` не рендерится как конкурирующий сюжет;
- semantic contract из родителя (`today-focus`, `today-focus-event`, state и
  content-state attributes) сохраняется.

Если `focus` отсутствует в старом payload, допускается controlled legacy branch;
если `focus` присутствует и имеет `contentState="unavailable"`, legacy headline
не является fallback и не должен появляться в focus-карточке.

Описание визуальной композиции добавляет отдельная дизайн-модель; она не
меняет selection semantics этого amendment.

---

## 7. Frozen / out-of-scope

- Формула factor ledger и family reducer.
- Расчёт `dayStatus`, `relativeStatus`, sphere valence/verdict.
- Grouping и ranking победившего convergence.
- Новый LLM-вызов, новая модель или увеличение token budget.
- Удаление legacy API-полей до consumer audit.
- Sidecar calculation changes: amendment использует уже существующие
  `exactAt`, strength, target и provenance.
- Визуальный дизайн.
- Исправление provider timeout, pregen retry, cache predicate или logging
  registry — это O1, не B2.1.

---

## 8. Acceptance tests

### 8.1. Pure unit

1. Winning convergence anchor всегда входит в selected set, если eligible.
2. Сильный exact factor из другой группы вытесняет слабый neutral factor из
   более высоко ранжированной группы.
3. После обязательного anchor два remaining slots следуют §3.3.
4. Нет forced positive balancing: три tense events допустимы, если они
   действительно первые по канону.
5. Physical signal+activation duplicate создаёт одно public event.
6. Невалидный machine-key title пропускается; селектор берёт следующего
   eligible кандидата.
7. Input permutation не меняет selected IDs и display order.
8. Selection cap всегда `0..3`; display order всегда `occurs_at+id`.
9. Один фирдар/return без сегодняшнего anchor не создаёт public event.
10. `single_impulses` использует общий pool без reserved convergence anchor.
11. `background_only|no_accent` возвращают `events=[]`.
12. Sanitized canary 28.07 возвращает три ID и время из §4.
13. Два запроса одной даты в разное wall-clock время дают одинаковый selected
    set при одинаковом canonical input/cache identity.
14. Public `event.id` и `sourceActivationIds` соответствуют §3.1.1; ни один
    activation ID не теряется при dedup.
15. `occurs_at=None` не вызывает exception и сортируется после timed events,
    без сгенерированного времени.
16. Convergence/independent partition из §3.5 инвариантен к permutation
    входных факторов.
17. Фактор без human-title eligibility пропущен с явным reason code, а не
    опубликован с machine key.

### 8.2. Contract/integration

1. Все `sourceActivationIds` selected events существуют в activation layer
   либо явно трассируются к canonical ledger factor.
2. Cache miss и fresh pregen возвращают одинаковые selected IDs/order.
3. Старый cache/content version не используется как current.
4. LLM mock не может изменить selected set/time/order.
5. `convergence_today|single_impulses` после C2 никогда не возвращает
   `contentState="not_needed"`.
6. `v2.activationSummary` с другой победившей темой не меняет `focus` и не
   становится UI source of truth.
7. Audit печатает sanitized focus section и завершает invariants `OK`.
8. B2.1 не проходит gate при незакоммиченном/непринятом C2 или при
   неоднозначном reducer audit.

### 8.3. UI semantic acceptance

1. На экране ровно один пользовательский сюжет «Что сошлось именно сегодня».
2. При `convergence_today` показаны backend events и 1–3 featured spheres.
3. Остальные сферы не получают ложный текст «сошлось сегодня».
4. При `contentState="unavailable"` факты/время остаются, LLM-copy отсутствует,
   отображается честный status message.
5. Тесты опираются на `data-testid`, `data-state`, `data-content-state` и
   event IDs/kind, а не на случайный LLM-текст.

---

## 9. Verification

Минимум:

```bash
cd apps/api
source .venv/bin/activate
python -m pytest tests/test_today_focus_builder.py -q
python -m pytest tests/ -q -k "focus or day_contract"
```

Live/sanitized audit после backend rollout:

```bash
make audit-day-live DATE=2026-07-28
```

Безопасный fixture-only запуск и ожидаемый allowlist описаны в
`30_TZ_W4_CANARY_SANITIZED_FIXTURES.md`; live audit не должен печатать полный
payload пользователя.

Audit должен доказать:

- `state=convergence_today`;
- convergence theme = Pluto;
- selected IDs и локальное время соответствуют §4;
- event cap/date/timezone/source invariants проходят;
- factual output сохраняется при simulated LLM timeout.
- O1 cache/pregen gate пройден: unavailable не считается успешным прогревом,
  а current cache содержит тот же state/events/order, что и fresh build.

---

## 10. Expected evidence и escalation

Кодер предоставляет:

- diff по exact scope;
- результаты unit/integration verification;
- sanitized audit section до/после;
- объяснение content-version bump;
- подтверждение, что C2 prompt/LLM ownership не изменены.
- clean C2 commit/review и reducer audit приложены до B2.1 diff.
- identity/provenance и null-time invariants проверены на sanitized fixture.

Нужна правка grouping, valence, sidecar, wire schema, второй LLM-вызов либо
удаление legacy API-полей — стоп и отдельное согласование. Ничего не коммитить
и не пушить.
