# MASTER TZ: Today Convergence Rewrite — `today-convergence-2`

Дата: 2026-07-30
Версия: **v1.12** (2026-07-30) — зарегистрированы обязательные W2/W7 start-gates из code-coverage audit и закрыты Yesterday/migration UX gaps; W1 formula/canon и replay fingerprint остаются frozen. v1.0–v1.11 superseded как редакции master.
Статус: **W1 frozen; implementation pack ready; W2 ready to start.** Единственный источник нормативов для нового экрана Дня и его потребителей (Calendar, Yesterday, check-in, pregen). Legacy test fixtures заменяются в W7, публичные generated roots — в W8, оставшийся недостижимый runtime удаляется по `W9_LEGACY_REMOVAL_MANIFEST.md`; в новый контракт ничего из старого не переносится.
Суперсидит: `docs/work/2026-07-27_today-premium-first-screen/00_MASTER_TZ.md` (FROZEN / SUPERSEDED, последний принятый SHA `0d4b265a`, волна W6 закрыта).
Исполнитель W1 freeze: Codex. Исполнитель W2 назначается отдельно; остановленный coder-loop не считается активным исполнителем.
Коммит/пуш: только ревьюер.

**Audit lineage:** `audit/01_W1_FREEZE_REALITY_CROSS_CHECK_CLAUDE.md` —
исторический REVISE до owner/freeze-решений и не является текущим вердиктом.
Его блокеры закрыты в master/canon/attestation. Текущая цепочка:
`audit/03_IMPLEMENTATION_PACK_AUDIT.md` — PASS и
`audit/04_CODE_COVERAGE_AUDIT_CLAUDE.md` — PASS с обязательными executor-gates
§8, перенесёнными в профильные ТЗ этой редакции.

## 1. Зачем rewrite

Детерминизм и контракты старой модели подтверждены тестами, но модель не совпадает с ощущением дня. Системные причины:

- глобальный dayStatus считается по всему ledger, включая фон → «все дни тяжёлые» (`apps/api/app/services/day_valence_service.py:313`);
- convergence объявляется по числу техник на target, а не по независимым событиям сферы (`apps/api/app/services/semantic_v2_service.py:238`);
- неизвестный фактор падает в work (`apps/api/app/services/today_focus_builder.py:271`);
- выбирается одна winning group, остальные сферы выбрасываются (`today_focus_builder.py:815`);
- LLM-тексты шаблонны (универсальные советы, переносимые в любой день);
- **инфляция convergence**: probe (81 день) показал 100% дней со схождением; правило «major ИЛИ slow = strong» даёт hero 81/81; без Луны — 62/81 (`01_PROBLEM_CONVERGENCE_INFLATION.md`). Корень: почти любой raw-факт считается независим подтверждением;
- **ложная полуденная карта**: при неизвестном времени рождения Today/Calendar молча подставляют 12:00 (`today_service.py:334`, `calendar_service.py:316`), натал-контекст при этом считает профиль неполным (`natal_context_service.py:95`) — пользователь местами блокируется, местами получает выдуманную карту (§4.7);
- **секта в Whole Sign флипается без физической причины**: high-latitude fallback в WHOLE_SIGN (`apps/solarsage/solarsage/utils/ephemeris.py:168`) + определение секты как `Sun house >= 7` (`apps/solarsage/solarsage/services/activation_builder.py:116`) — в Whole Sign номер дома Солнца ≠ физическое положение над горизонтом (§4.4).

**Смысл rewrite: мы не ищем пустые дни — мы отделяем редкое настоящее «сошлось» от обычных ежедневных импульсов.**

V1/V2/V2.1/V2.2-линейка дала нормативный drift (три коррекции valence за неделю). Решение владельца: полный rewrite, контракты рвём осознанно, legacy-код не тащим. Механизм версий (formula_version + replay) сохраняем.

## 2. Суперсединг

### Переиспользуем (код и нормативы остаются в силе)

- **принцип** ledger/timing/provenance и public event selection. Текущий `factor_id` НЕ является стабильным canonical ID — identity определяется заново (§4.2);
- bounded LLM-фаза: единый `deadline_at`, provider timeouts `min(60, remaining)`, DeepSeek provider-fallback при remaining ≥ 15s, проброс `CancelledError` (W6-S4a, `0d4b265a`);
- schema-валидатор state×content_state + caps + dup IDs — **с новой матрицей** (§5.2);
- честный cache: `unavailable` никогда не «тёплый»;
- запрет fallback-копирайтинга (`21_TZ` §6.6) — норматив в силе без изменений;
- sanitized fixtures (30_TZ); локальное время в LLM evidence (фикс §3.3);
- композиция первого экрана из W1, уже в main, — как текущее состояние до замены волной W7.

### Суперсидим (удаляется по волнам §13)

- глобальный dayStatus (supportive/steady/tense) как продуктовый результат;
- relative zone как механизм, способный переопределять фактические события;
- ежедневные вердикты всех 12 сфер (навигатор становится статическим — D8);
- «три слоя» (anchor/supporting/background) как продуктовая модель — остаются внутренней timing-классификацией; background вообще не участвует в группах (§4.3);
- convergence по числу техник (SemanticV2Service);
- fallback неизвестной сферы в work;
- единственная winning group;
- fallback `find_house(...) or 1` (§4.4) и `birth_time or "12:00"` (§4.7);
- мёртвый delta-trigger: DayDelta отдаёт голые имена планет, `classify_temporal_role` сравнивает с полными factor_id — ветка не срабатывает никогда (§4.3.1);
- fan-out факторов по множеству сфер, из-за которого один физический сюжет производит 4–9 «групп» (§4.5);
- `ORB_FALLBACK=6.0` для источников вне orb-профиля (§4.4);
- определение секты через номер дома Солнца (§4.4);
- V1/V2/V2.1/V2.2-контракты и valence-линейка (12–17_TZ старого master);
- старый master как источник нормативов.

### Граница rewrite: старые контракты не переносятся

Полный rewrite — это новая контрактная поверхность, а не V3-адаптер старого
Today-пути. В новую версию **не переносятся и не поддерживаются через dual-read/
dual-write**:

- старые API/Pydantic/Zod-типы состояний (`single_impulses`, `background_only`,
  `no_accent`, legacy `dayStatus`/`relativeStatus`);
- старые frontend-компоненты Today/Calendar/Yesterday, завязанные на эти поля,
  их `data-testid`, fixture payloads и visual/e2e baselines;
- старые V1/V2/V2.1/V2.2 response-shapes, valence-поля, winning-group и
  fallback-тексты;
- старые consumer-адаптеры, которые молча переводят новый результат в legacy
  enum или сохраняют оба контракта одновременно.

Новая frontend/API связка строится только на envelope §5 и его `formulaVersion`;
старый UI не является fallback для нового snapshot. Старый production runtime
можно оставить работающим до атомарного W8 cutover. Активные test fixtures
заменяются в W7, legacy roots исключаются из generated contract перед W8 build,
а оставшийся недостижимый код удаляется отдельным W9 cleanup-релизом.
Git-история — единственный архив старой реализации; совместимость с ней не
входит в scope rewrite.

Это правило **не распространяется** на protected user data, auth, payments,
subscriptions, профили и существующие check-in/streak записи: они сохраняются и
мигрируют additive-полями по §11. Удаляются только legacy derived Today/cache/
semantic/history rows после dump и restore rehearsal.

### Переносим в новый план

- typed pregen outcomes / retry / telemetry (бывший W6-S4b) → волна W5 (§13).

## 3. Продуктовые решения (закрыты, не обсуждаются в срезах)

- **D1. Публичные состояния — три.** `convergence_today` (есть hero-eligible convergence) | `quiet_day` (обычные импульсы, medium-кандидаты или отсутствие импульсов после фильтра) | `unavailable` (расчёт технически не получен/невалиден). `no_signal`/`no_public_signal` и `single_impulse` как UX-состояния **упразднены**. (Маркированный «общий фон дня» — корректный крайний контракт внутри quiet_day, §4.7; в текущем корпусе не срабатывает.)
- **D2. quiet_day.** Показывает 0–3 отранжированных импульса («Импульсы дня», значимость ↓ → время ↑ → factor_id ↑), каждый со временем и сферой, плюс нейтральный детерминированный контекст. Слово «сошлось» не показывается. При пустом наборе текст не выдумывается — только детерминированный контекст периода.
- **D3. Tense-подача (расчёт не цензурируется, регулируется канал).** High → hero: конкретная тема + время пика + конструктивный хвост. Medium → строка «зона повышенного внимания», спокойный тон. Движок всегда возвращает честно рассчитанные polarity и evidence_level. **Push/opt-in из rewrite v1 исключены** — отдельный master после cutover.
- **D4. Несколько tense одновременно.** Один hero (максимальный evidence) + до двух вторичных строк по 5–7 слов. Цвет tense — янтарный; красная тревога запрещена везде.
- **D5. evidence_level, не confidence.** Публично: `high` (hero-eligible) / `medium` (значимые связанные units без rare/structural). `low` упразднён как публичный уровень (diagnostic only). Переименование в confidence — только после живой валидации (§14).
- **D6. Копирайт-канон (§8).** Конкретный тон с привязкой к фактору — подтверждён владельцем. Тест переносимости, валидатор привязки, блэклист, claim binding, запрет выдуманных жизненных событий.
- **D7. Hero — нормативное правило (C1, утверждено владельцем):**

  ```text
  Hero = rare/structural фактор, точный именно сегодня,
       + минимум одна независимая non-background evidence-единица,
       + прямая связь по target/theme,
       + устойчивая сфера и полярность.
  ```

  Дополнения: weight ≥ 0.55, orb_ratio ≤ 0.5; lunar_return и monthly_profection НЕ rare_anchor_eligible (остаются supporting/context); продолжающиеся фирдары/профекции/возвраты — background; Луна/Меркурий/Венера — публичные импульсы, но в C1 v1 НЕ засчитываются как независимое hero-подтверждение; background не второй unit и не соединяет группу; транзитивные мосты запрещены. Измеренные частоты (мониторинг, НЕ квота): exact 8/81, buckets 1–2/81, unknown 1/81 — неопределённость времени честно сокращает hero. Запрещено публичное обещание «точное время даст в N раз больше особенных дней» — результат одной карты и одного сезона.
- **D8. Навигатор 12 сфер — статический.** Тайл = иконка + одно слово, фиксированный канонический порядок (work, money, documents, relationships, sport, communication, health, decisions, travel, creativity, study, shopping), тап = вся площадь. Без дневных вердиктов/чипов/бейджей/стрелок. Единственный маркер — нейтральная точка «есть разбор сегодня» у выбранных сфер; НЕ красится по polarity и ведёт в drilldown (D10), а не на статику. Компоновка — §16.
- **D9. Lookahead — только из frozen snapshot.** Строка «Завтра факторы сходятся в …» допустима в quiet_day и только если завтрашний snapshot уже заморожен pregen'ом; иначе блок скрыт. Исключён из engine-валидации.
- **D10. Drilldown выбранной сферы — «Почему сошлось».** Доказательная цепочка: драйверы с временами и окнами, основание связи, period context сферы. Полностью детерминирован. «Полный разбор дня» и «Почему так у меня» из экрана дня удаляются.
- **D11. Главное событие дня.** Одно исключительное редкое событие (без второго независимого) показывается как «Главное событие дня» внутри quiet_day — НЕ называется «сошлось».
- **D12. Неопределённое время рождения (P0, §4.7).** Три режима: `exact | bucket | unknown`. Никакой подстановки условного полудня. Пользователь без времени — полноценный аккаунт с менее детальным, но честным расчётом: только факты, устойчивые по всему диапазону неопределённости. Часы событий — только при exact; иначе часть суток или дата.
- **D13. Nightly pregen — не для всей базы и не один большой LLM-вызов.** Ночью выбирается только cohort пользователей с недавней активностью (текущий baseline: session за последние 14 дней), полным birth identity (`birthday`, birth timezone, latitude, longitude) и допустимым доступом к Дню. Для cohort сначала строится детерминированный factual snapshot; LLM warm-up выполняется только для разрешённой тёплой подкогорты по access/engagement policy W5. Dormant users не прогреваются и получают расчёт по запросу. Failed/`unavailable` результат не считается успешным прогревом и ставится на retry. Неувиденный snapshot не участвует в live-валидации: check-in связывается только через `forecast_snapshot_id` + server-side `prediction_seen_at` (§6.3–§7).
- **D14. Owner freeze decision (2026-07-30).** Population replay `120 × 730 × 6` принят как W1 baseline: exact hero-rate `4.9041%` (`1.47/30d`), а не продуктовая квота/SLA; прежняя гипотеза `8–20%` superseded и остаётся только исторической. `tone-candidate-0.1` принят как W1 tone policy: exact tense `4.7728%`, mixed `6.1199%`, supportive `6.4612%`, steady `82.6461%`. Это доказывает механику и распределение, но не корреляцию с жизнью; последняя проверяется только snapshot-linked check-in (§14).

## 4. Модель: pipeline

### 4.1 Сырые события (raw facts)

Все рассчитанные факты (~150 параметров дня). **Не удаляются** — нужны аудиту и replay. В публичную evidence-модель не попадают напрямую.

### 4.2 Canonical event ID

Один физический факт = один canonical ID во всех слоях. Identity = versioned хэш нормализованных физических полей + event window, НЕ зависит от producer-пути. Producer precedence обогащает provenance, не меняет identity. Префиксы `Transit_`/`Natal_` стриппятся. Mutation-тест producer parity обязателен. **Canonical ID устраняет технические дубли, но НЕ делает свидетельства независимыми.**

### 4.3 Пятислойная evidence-модель

```text
raw fact → significant impulse → independent evidence unit → hero convergence → presentation
```

1. **Raw fact** (§4.1). Timing-метки (точный пик сегодня / начинается сегодня / новая фаза / активно ранее / фон; локальный день пользователя `current_tz → birth_tz → UTC`) ставятся здесь.
2. **Публично значимый импульс** — raw fact, прошедший порог значимости. Для аспектов: вес аспекта (≥ 0.55), orb_ratio (≤ 0.5), вес источника. Для не-аспектных факторов (time-lord, house-ингрессии): пороги по `event_class` — **автоматический pass запрещён**. Таблица порогов — machine-readable canon W1.
3. **Независимая evidence-единица** — трёхуровневая eligibility (§4.3.1): `impulse_eligible ⊇ evidence_eligible ⊇ rare_anchor_eligible`. Быстрые источники (Луна, Меркурий, Венера) — impulse и evidence, но НЕ rare_anchor и (в C1 v1) НЕ независимое hero-подтверждение. Независимость — по `driver_key`/`technique_horizon`: два быстрых аспекта одного driver/horizon — НЕ два свидетельства.
4. **Hero convergence** — по нормативному правилу D7. **Background НЕ участвует в группах вообще**: ни членом, ни свидетелем, ни в independence count — только контекст уже сформированной группы. Только direct relation; транзитивный bridge запрещён.
5. **Presentation** — hero ↔ `convergence_today`, quiet ↔ `quiet_day` (T4/T5, §4.6).

#### 4.3.1 Machine-readable canon evidence-единицы (W1, обязателен)

Каждая canonical event / evidence unit несёт поля:

```
driver_key, technique_horizon, event_class,
source_key, target_key, target_type, target_salience,
aspect_type, orb, max_orb, orb_ratio (peak_exactness),
exact_at, phase, active_from, active_until,
data_quality,
impulse_eligible, evidence_eligible, rare_anchor_eligible,
exclusion_reason,
birth_time_mode, birth_time_robustness (robust | time_sensitive)
```

В W1 формально определяются (не прозой, а таблицами канона):

- когда два события имеют один `driver_key`;
- какие technique horizons независимы;
- какие target types допустимы для hero (диагностическая отправная точка: planet/angle; lots — кандидат на исключение);
- реестр `rare_anchor_eligible` классов (медленные мажорные транзиты, структурные лунные события eclipse/lunation, time-lord смены периода и т.п.; **lunar_return и monthly_profection исключены** — supporting/context);
- пороги значимости по `event_class` для не-аспектных факторов (без auto-pass);
- **контракт DayDelta: `new_today`/`peak` несут canonical event IDs / semantic keys, а не голые имена планет** (сейчас ветка `is_delta_trigger` мёртвая; сравнивать по имени планеты нельзя — это сделает якорями все факторы той планеты);
- поведение при неизвестном времени рождения / низком data_quality (§4.7);
- fan-out: один фактор, проецируемый в несколько сфер, НЕ создаёт искусственные независимые группы (§4.5);
- допустима только direct relation; транзитивный bridge в connected components запрещён (A→B→C не объединяет несвязанные группы).

### 4.4 Fail-closed входные данные

- `planet.house` приходит от sidecar либо равен null. Fallback `or 1` запрещён (`normalization_service.py:155, 217`): null исключается с reason code, растёт `invalid_events`.
- Подстановка `birth_time or "12:00"` запрещена везде (§4.7).
- `ORB_FALLBACK=6.0` для источников вне orb-профиля запрещён: для каждого источника в каноне явный `max_orb`, иначе источник исключается fail-closed.
- **Секта (day/night) — новое правило:** определяется **геометрической высотой Солнца над горизонтом в дату и место рождения**, НЕ номером дома и НЕ системой домов. Корень старого бага: high-latitude fallback в WHOLE_SIGN (`ephemeris.py:168`) + `sect = Sun house >= 7` (`activation_builder.py:116`) — в Whole Sign знак ASC = дом, и при смене знака ASC секта скачет без физической причины. `sun_house = null` НЕ превращается автоматически в day chart (fail-closed). Для диапазона, пересекающего восход/закат, sect-зависимые факторы (фирдар и др.) — `time_sensitive`. Сравнение — с восходом/закатом в дату и место рождения, не прогнозируемого дня. Исправляется в движке ДО freeze W1.
- Изменение контракта sidecar → атомарный deploy + contract tests (§11).

### 4.5 Проекция на сферы

Порядок изменён (запрет fan-out): **физическая группа по target/direct relation → одна canonical convergence → проекция группы в primary sphere → максимум одна secondary sphere.** Не факторы размножаются по сферам, а группа получает сферу(ы) целиком. Unmapped-фактор исключается (audit `excluded_unmapped`). `decisions` больше не catch-all: в planet-map она разрешена только SATURN/PLUTO; technical theme может добавить её только по явному канону. Один фактор виден в нескольких сферах, но при подсчёте остаётся одним фактором (§4.3.1 fan-out).

### 4.6 Truth tables (финальные)

**T1. Eligibility hero-convergence:** нормативное правило D7: ≥1 rare/structural якорь дня + ≥1 независимая non-background единица + ≥1 сегодняшняя динамика + direct связь target/theme + устойчивые сфера и полярность.

**T2. Polarity группы:** `supportive | tense | mixed`. Считается по independent units, не по raw-дублям; смешанный фактор делится; равенство → mixed.

**Tone policy (W1, owner-approved):** общий `day_tone` не выводится из наличия
одного tense unit. Сначала разделяются `unit_polarity` → `group_polarity` →
`day_tone`; supporting-длинные темы остаются контекстом, быстрые источники не могут
в одиночку создать общий tone. Полная truth table и audit-поля —
`02_TONE_POLICY_AMENDMENT.md` и `grace/canon/today_convergence.v1.yml`;
tone-aware corpus replay пройден, `tone-candidate-0.1` принят решением D14.

**T3. evidence_level:**

| level | условие |
|---|---|
| high | hero-eligible (T1 выполнено) |
| medium | есть значимые связанные units, но нет rare/structural якоря дня |

`low` из публичной модели удалён (diagnostic only).

**T4. Presentation:**

| state | блок |
|---|---|
| convergence_today | hero «Что сошлось сегодня» (1–3 сферы) |
| quiet_day | 0–3 импульса + optional main_event + нейтральный контекст; слово «сошлось» запрещено |
| unavailable | честный статус; персональный snapshot и частичные факты не публикуются |

**T5. Root state:** `convergence_today | quiet_day | unavailable`. State и presentation согласованы 1:1.

**Выбор 0–3 сфер:** evidence ↓ → evidence_level ↓ → канонический порядок сфер.

### 4.7 Неопределённое время рождения (P0)

**Принцип:** расчёт по диапазону неопределённости и пересечение устойчивых фактов — НЕ подстановка условного полудня. Пользователя без времени не выключаем: он получает менее детальный, но честный персональный расчёт.

**Профильный контракт (храним неопределённость, не выдуманное среднее):**

```
birth_time_mode: exact | bucket | unknown
birth_time: HH:MM | null            — только при exact
birth_time_bucket: night | morning | day | evening | null
```

Границы bucket'ов — в canon и всегда трактуются как полуоткрытые интервалы
`[start, end)` локального времени места рождения: night `[00:00, 06:00)`,
morning `[06:00, 12:00)`, day `[12:00, 18:00)`, evening
`[18:00, 24:00)`. Пары `buckets_local: [start_hour, end_hour]` в frozen canon
— YAML-последовательности с этой же семантикой, а не замкнутые математические
интервалы. `unknown` = `[00:00, 24:00)`. Миграция: существующий
`birth_time = null` → `unknown`, непустое → `exact`.

**Profile readiness ≠ расчётные возможности.** Отсутствие времени НЕ делает аккаунт незавершённым (`birth_time` уходит из обязательных полей натал-контекста, `natal_context_service.py:95`). Возможности выводятся из режима:

| Режим | Разрешено |
|---|---|
| exact | полная карта: дома, ASC/MC, лоты, точный тайминг |
| bucket (утро/день/вечер/ночь) | только факты, устойчивые внутри bucket'а; дома, углы, лоты НЕ показываем |
| unknown | только факты, устойчивые в пределах всех суток |

**Расчёт устойчивости — схема sparse/oracle:**

- **production:** фиксированная редкая каноническая сетка контрольных времён (для unknown обязательно включает конечную точку 23:59); что считаем — объявлено явно и воспроизводимо;
- **запас по орбу (orb-margin)** выводится из скорости объекта и максимального промежутка между точками сетки — НЕ выбирается вручную;
- **offline replay:** плотная oracle-сетка;
- **gate:** `published_sparse ⊆ robust_dense` — редкая сетка может потерять факт, но НЕ имеет права опубликовать неустойчивый. Это и есть финальная формулировка fixture 9 (фиксированная сетка сама по себе даёт воспроизводимость, но не истинность «устойчив во всём диапазоне»);
- аспект, полярность или сфера, меняющиеся от контрольного времени, → `time_sensitive` (`exclusion_reason = time_sensitive`);
- несколько контрольных точек одного факта = ОДНА evidence-единица (замерено: dedup 3.4–6.2×);
- LLM вызывается один раз, уже после агрегации;
- Луна не запрещена автоматически: устойчивые в диапазоне знак/аспект — можно; меняющиеся — исключаются;
- sect-зависимые факторы для диапазона, пересекающего восход/закат, — `time_sensitive` (§4.4).

**Влияние на evidence (birth_time_robustness):**

- convergence — только из независимых И устойчивых драйверов;
- факт, существующий лишь для части диапазона, не может стать hero;
- расхождение полярности между контрольными точками исключает публичный вывод;
- часы события — только при `exact` И устойчивом тайминге; иначе часть суток («во второй половине дня») или только дата.

**Честный «общий фон дня» (вариант quiet_day с `personal: false`, корректный крайний контракт — ОСТАВЛЯЕМ):** если после фильтрации не осталось персонально устойчивого — показываем отдельно маркированный общий фон неба дня, НЕ выдаём за персональный прогноз. В текущем корпусе не срабатывает (0/81 во всех стратах, ~59–65 устойчивых фактов/день даже при unknown), но контракт сохраняется: измерения — одна карта, до финальных правил sphere/background.

**Контрактная целостность:**

- precision/range добавляются в API, БД, profile hash, cache key и published snapshot (`birth_time_mode`, фактически использованный диапазон);
- все fallback'и `birth_time or "12:00"` на новом Day/Calendar call graph
  удаляются (`today_service.py:334`, `calendar_service.py:316`); новый pipeline
  использует только explicit mode/range. Отдельное совпадение в Synastry не
  входит в этот rewrite и не может переиспользоваться новым Day-путём;
- в LLM передаются capabilities: `houses_available`, `angles_available`, `lots_available`, `exact_timing_available`; валидатор отклоняет упоминания домов/ASC/MC/lots/точных часов при недоступности;
- переход `unknown/bucket → exact`: пересчёт будущих данных, новая версия snapshot; опубликованные прогнозы не переписываются (§6);
- UI-формулировка (спокойная, один раз): «Покажем только то, что не зависит от точных минут рождения. Дома и точные часы событий использовать не будем. Время можно уточнить позже».

## 5. Публичный контракт

### 5.1 Root envelope (скетч; полная runtime-схема — `04_W2_W3_RUNTIME_CONTRACT_TZ.md`)

```json
{
  "schemaVersion": 1,
  "snapshotId": "…",
  "targetDate": "2026-07-30",
  "timezone": "Europe/Moscow",
  "publishedAt": "2026-07-30T01:07:00Z",
  "access": {"state": "full | preview | locked", "reason": "…"},
  "birthTime": {"mode": "exact | bucket | unknown",
                "capabilities": {"houses": true, "angles": true,
                                 "lots": true, "exactTiming": true}},
  "state": "convergence_today | quiet_day | unavailable",
  "dayTone": "supportive | tense | mixed | steady | null",
  "personal": true,
  "previewTeaser": null,
  "convergences": [
    {"id": "cvg_1", "primarySphere": "work", "secondarySphere": null,
     "polarity": "tense", "evidenceLevel": "high",
     "eventIds": ["evt_1", "evt_2"], "summary": null}
  ],
  "mainEvent": null,
  "impulses": [],
  "periodContext": null,
  "lookahead": null,
  "events": [],
  "contentState": "ready | pending | unavailable | not_needed",
  "formulaVersion": "today-convergence-2",
  "calculationVersion": "ss-calc-1.3.0"
}
```

**Ортогональность:** calculation state ≠ content state ≠ access state. Locked payload НЕ создаёт и не публикует snapshot; `snapshotId` nullable только там, где персональный прогноз не опубликован. Contract-test прогоняет один source fixture через три access-проекции и доказывает, что preview/locked не раскрывают скрытые поля.

### 5.2 Матрица state × contentState

| state | допустимые contentState |
|---|---|
| convergence_today | ready, pending, unavailable |
| quiet_day | ready, pending, unavailable, not_needed |
| unavailable | unavailable |

`contentState=unavailable` → все LLM-owned поля null, детерминированные события/сферы остаются (21_TZ §6.6).

### 5.2.1 Матрица state × dayTone × contentState

`dayTone` — детерминированное поле расчёта, не поле LLM и не синоним `state`.

| state | допустимый dayTone | допустимые contentState | presentation invariant |
|---|---|---|---|
| `convergence_today` | `supportive \| tense \| mixed \| steady` | `ready \| pending \| unavailable` | Показывается convergence; tone не меняет факт hero |
| `quiet_day` | `supportive \| tense \| mixed \| steady` | `ready \| pending \| unavailable \| not_needed` | Показываются 0–3 импульса/контекст; `steady` не означает пустой экран |
| `unavailable` | `null` | `unavailable` | Персональный расчёт не публикуется; не создавать выдуманный tone |

`quiet_day + tense` не называется «тяжёлым днём» без hero: UI использует
конструктивную «зону внимания». `quiet_day + steady` не получает empty-state.
`contentState=unavailable` не обнуляет уже рассчитанные `dayTone`, события или
сферы — обнуляются только LLM-owned поля.

`state` nullable только при `access.state=locked`. Для `state=unavailable`
персональный snapshot отсутствует; это не то же состояние, что LLM-сбой
`contentState=unavailable`. Полная wire-матрица и правила nullability — в
`04_W2_W3_RUNTIME_CONTRACT_TZ.md`.

### 5.3 Cache и latency

- factual snapshot отдаётся сразу, даже при `contentState=unavailable`; повторный GET НЕ запускает новый provider-call на каждый refresh;
- single-flight: один generation lease + cooldown на `(snapshot_id, prompt_version)` (`today_service.py:1175–1211` сейчас без lease);
- `contentState=unavailable` не считается успешным прогревом (норматив W6-S4a в силе);
- SLO (цели W5): cache hit < 1 с; cold deterministic path ограничен bounded deadline;
- нагрузочный contract-test: 20 одновременных GET одного user/date при зависшем LLM.

### 5.4 Nightly pregen policy (реализация W5)

- **Calculation cohort:** недавно активные пользователи с полным birth identity;
  baseline `active_days=14` конфигурируем, но не выбираем всех пользователей из
  базы. Профиль с `birth_time=null` допускается как `unknown`, если дата/место/
  timezone заполнены.
- **Два этапа:** (1) deterministic calculation + immutable snapshot, (2) LLM
  warm-up только для access/engagement cohort. Snapshot не зависит от успеха LLM.
- **On-demand:** пользователь вне cohort или без LLM warm-up получает factual
  snapshot по запросу; разрешённый текст генерируется single-flight на
  `(snapshot_id, prompt_version)` и кэшируется.
- **Failure/retry:** `contentState=unavailable` не считается успехом pregen;
  сохраняется typed outcome, причина и retry с cooldown. Шаблонный персональный
  fallback запрещён.
- **Validation:** generated snapshot сам по себе не является impression. В
  check-in попадает только snapshot, который был показан и получил
  `prediction_seen_at`.
- **Capacity:** cohort selection, concurrency, provider budget, retry и telemetry
  задаются в W5 consumer matrix; ночной job не должен блокировать дневной запрос.

## 6. Snapshot и canonical input

### 6.1 Поля

```
snapshot_id, user_id, target_date, timezone,
profile_hash, input_hash, canon_hash,
formula_version, calculation_version, ephemeris_artifact_id,
created_at, published_at, first_day_seen_at, first_lookahead_seen_at,
state, deterministic_result, canonical_input_ref,
supersedes_snapshot_id,
birth_time_mode, birth_time_range
```

LLM content/status/lease хранится в отдельной versioned записи по
`(snapshot_id, prompt_version)` и не мутирует deterministic snapshot.

### 6.2 Identity и concurrency

- unique constraint: `(user_id, target_date, input_hash, formula_version, calculation_version, canon_hash)`;
- полная нормативная identity/lineage-схема — `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §7.1; при расхождении действует она;
- атомарный publish/claim (INSERT … ON CONFLICT DO NOTHING или эквивалент);
- `published_at` = атомарная публикация snapshot (включая pregen), не доказательство показа; после неё deterministic fields неизменяемы;
- исправление бага → новый snapshot с `supersedes_snapshot_id`: только внутри owner/date, без циклов;
- check-in FK validation: `snapshot.user_id == authenticated user` И `snapshot.target_date == checkin.target_date`;
- narrative rows удаляются CASCADE со snapshot; check-in FK — `ON DELETE SET NULL`;
- новые published snapshots не входят в W9 legacy cleanup; retention ≥ 180 дней до отдельной privacy/retention policy.

### 6.3 Impression

`prediction_seen_at` НЕ пишется в EveningCheckin напрямую (строки ещё нет).
Snapshot хранит два idempotent server timestamps: `first_day_seen_at` и
`first_lookahead_seen_at`. Для lookahead endpoint проверяет ссылку на завтрашний
snapshot из snapshot открытого дня. При первом submit check-in full-day exposure
имеет приоритет над lookahead; обычное редактирование не перепривязывает
lineage. Полный wire/ownership-контракт — `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §7.

### 6.4 Canonical input

Prod-таблица хранит только `published`; `canonical_input_ref` → immutable content-addressed normalized factor pack БЕЗ raw Telegram/profile полей. Hash serialization, SHA-256, версии engine/ephemeris/sidecar/formula/canon — канон. Replay-выход — offline-артефакт или job-result с TTL, НЕ `type=replay` в основной таблице. Проверка: byte-identical воспроизведение из lineage; privacy scanner чист.

## 7. Check-in (additive-миграция)

- `forecast_snapshot_id` (nullable, FK + owner/date validation §6.2) +
  `prediction_seen_at` + `prediction_seen_surface: day|lookahead|null`
  (nullable, из impression §6.3);
- один опциональный мультиселект «Что сегодня больше всего проявилось?» → `observed_spheres[]`;
- `target_date` check-in — локальный день пользователя на момент submit;
- `mood` — метрика резонанса дня, НЕ полярность сферы;
- constraint `(user_id, target_date)` и streak-логика не меняются;
- **DayFeedback (Telegram bot)**: в v1 исключён из engine-валидации. Напоминание «насколько попал прогноз» — только при наличии impression;
- приёмка: SQL однозначно соединяет каждый check-in с прогнозом, formula_version и предсказанными сферами.

## 8. LLM-роль и копирайт-канон

LLM получает только уже выбранные события и пишет человеческую формулировку. Не меняет сферу, polarity, время, count, evidence_level. Один компактный вызов, atomic validation; при сбое — null по 21_TZ §6.6 (provider-fallback допустим, текстовый fallback запрещён). Timeout-тест: ни одно LLM-поле не содержит универсального текста.

**Тон:** конкретный, с привязкой к фактору — подтверждён владельцем. Модальность не требуется; запрещены выдуманные факты.

**Claim binding (обязателен, W6):** каждый claim несёт source event IDs; время и окно подставляются детерминированно. Adversarial fixture: корректные IDs + выдуманный сценарий → validator отвергает весь atomic response. Валидатор дополнительно отклоняет упоминания домов/ASC/точных часов при соответствующих capabilities (§4.7).

**Тест переносимости**, **валидатор привязки**, **блэклист** («прислушайся к себе», «сохраняй спокойствие», «не принимай поспешных решений», «доверься интуиции») — как в эталонных парах:

```text
✗ Шаблон: «Реакции острее обычного — решения лучше принимать
  после паузы, не с первого импульса.»

✓ Меркурий–Сатурн (пик 15:40, окно до 18:00):
  «Тема сроков и обязательств обостряется, пик около 15:40.
  Разговор о дедлайне или деньгах в этот час легко зайдёт в тупик —
  если ответ не горит, перенеси его на вечер: после 18:00 напряжение
  спадает.»

✓ Марс–Плутон (пик 19:52):
  «Спор о контроле — кто решает, чей план, чьи деньги — сегодня
  быстро перерастает в борьбу за принцип. Если цель договориться,
  а не победить, уступи формулировку и забери суть.»

✓ Луна–Солнце (пик 19:24, окно до 21:00):
  «Два часа эмоционального фона: сообщение, написанное в этот вечер,
  утром покажется резче, чем ты имел в виду. Черновик — можно,
  отправка — завтра.»
```

## 9. Audit, mutation-тесты, replay-ablation

**Audit (персистится вместе со snapshot):**

```
raw_factors, canonical_events, duplicates_removed, invalid_events,
today_eligible_events, significant_impulses, independent_units,
convergence_groups, selected_spheres,
excluded_background, excluded_unmapped, excluded_noise,
excluded_time_sensitive, invariant_failures
```

**Ablation-логика — committed script в `analysis/`** (не история сессии): `analysis/ablation_harness.py` + `ablation_grid*.json` + `ablation_report*.md` + `ablation_birthtime*.md`.

**Политика коммита артефактов:** в репозиторий — исполняемые скрипты, MD-отчёты, компактный summary JSON, checksum и команда воспроизведения. Сырые дампы (`factor_dump*.json`, `convergence_probe_results.json`, 100+ МБ) — gitignored или внешнее хранилище.

**Исправленный replay перед freeze W1:** полный прогон `120 карт × 730 дней × 6 режимов` выполнен новым классификатором для трёхуровневой eligibility, background-out, direct grouping, суженного rare-set, event_class, ORB fail-closed, DayDelta identity и геометрической sect; lineage — source fingerprint `90c691f0…`. Sphere registry был уточнён после этого прогона. Повторный ephemeris replay для него не требуется только при зелёном semantic-delta gate: старый и новый mapping распознают один и тот же набор planet/technical keys; `state`, hero IDs и `dayTone` byte-equivalent; меняются только projected primary/secondary; каждая группа имеет `≤2` сферы. Оба fingerprint и команды доказательства записываются в freeze delta-attestation. Любое нарушение этого gate возвращает требование полного replay.

**Invariants (replay обязан проверять):**

1. добавление raw noise не повышает hero;
2. дубль не меняет результат;
3. схлопывание двух событий одного driver не создаёт второй unit;
4. удаление одного из ровно двух units убирает hero;
5. edge-orb factor попадает в `excluded_noise`;
6. background без current anchor не создаёт группу;
7. перестановка входа не меняет результат;
8. producer parity сохраняет canonical ID;
9. TZ/DST меняют только локальную классификацию;
10. fan-out одного фактора по сферам не создаёт независимое evidence;
11. `published_sparse ⊆ robust_dense` (birth-time gate).

**Mutation fixtures (явные, изолированные):**

1. два обычных лунных аспекта одного target → не hero;
2. тот же driver двумя producer-путями → один unit;
3. фактор на границе orb → excluded noise;
4. две независимые техники на одном target → hero только при rare/structural;
5. транзитивная цепочка A→B→C не объединяет несвязанные группы;
6. исключительное одиночное событие → `main_event`, не convergence (**W2 presentation gate; не расчётный W1 fixture**).

**Birth-time fixtures (P0):**

7. неизвестное время нигде не превращается в 12:00 (rg + runtime guard);
8. unknown не выпускает дома, ASC/MC и лоты;
9. sparse-результат ⊆ oracle-результату по всем стратам (gate §4.7) — PASS. Старая byte-identity проверка переименована в `diagnostic_shifted_grid_sensitivity` со статусом OBSERVED (не FAIL): остаток — консервативная полоса маржи (27–32/бакет) + genuinely time-sensitive факты (29 profection-флипов на краю 05:00→05:59) — разбор в `ablation_sect_oracle.md` §6;
10. противоречащая полярность между контрольными точками не становится hero;
11. sampling не размножает evidence (N контрольных точек = 1 unit);
12. LLM вызывается один раз на payload (**W6 gate**);
13. unknown → exact меняет hash/cache, но не старый published snapshot (**W3 gate**).

**Replay-корпус до freeze W1:** 100–200 карт × 2–3 года; разные широты, TZ/DST; **отдельные прогоны для exact, каждого из 4 bucket'ов и unknown**. Отчёт: impulse count, independent units, hero rate, sphere fan-out, noise exclusions, time_sensitive exclusions, tense streaks (**только по выбранным публичным units**), latency.

**Пороги НЕ выбираются для попадания в квоту.** Гипотеза частоты hero ~8–10% — мониторинг, не gate. Измеренные точки: exact 8/81, buckets 1–2/81, unknown 1/81. Отклонение → явный пересмотр определений.

## 10. Blast radius

- Calendar chips (`calendar_service.py:184–266`, включая кэш);
- Yesterday screen; check-in forecast hint (`checkin-screen.tsx:261`);
- readings (`lib/api/readings.ts:70–82`); election;
- DaySummaryCard / DayChart / WeekStrip; focus-event drilldown (`api/day.py:180+`);
- audit-скрипты; semantic cache, score history, contract fixtures;
- pregen (`apps/api/app/jobs/day_pregen.py:113`);
- Telegram DayFeedback (`models.py:856`, `telegram_webhook.py:114–137`);
- onboarding (`components/onboarding/step-birth.tsx`), profile schema (`schemas/profile.py:85`), natal context readiness (`natal_context_service.py:95`), все `birth_time or "12:00"` (rg);
- DayDeltaService (контракт new_today/peaks) и `classify_temporal_role` (§4.3.1);
- **sidecar: sect (§4.4), house-контракт, контрольные времена (§4.7)** — входит в атомарный release (§11).

**Consumer matrix (обязательна в W5):** `consumer → поля → какой snapshot → access rule → cache key`, включая строку «календарный месяц» (дни вне pregen-окна — пустые чипы, НЕ старый valence). Drilldown адресуется через snapshot/event identity.

**Обязательный фикс в W2/W5:** единый resolver локальной даты пользователя
используется day/today, calendar, drilldown, yesterday, check-in и pregen вместо
UTC-даты (`api/day.py:133–139`); contract suite вокруг полуночи и DST. Точный
контракт — `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §5.

**Legacy-removal gate (W9):** `rg "dayStatus|relativeStatus|ScoringV2|DayValence|SemanticV2|today\.v2"` — каждое совпадение удалено или обосновано.

**Rewrite contract gate (W7/W8/W9):** `rg` по старым TodayFocus enums, legacy
`contentState`-матрицам, old `data-testid`/fixture payloads и V1/V2 response
shapes должен вернуть только supersession-документацию или Git-архив. Старые
frontend/API contracts не адаптируются в новый envelope: fixtures заменяются в
W7, generated public roots исчезают до W8 build, implementation удаляется W9.

## 11. Деплой и rollback

- DB-изменения сначала additive: новые поля (`birth_time_mode`, `birth_time_bucket`, `birth_time_prompt_dismissed`, snapshot precision/range) с миграцией существующих (`null birth_time → unknown`, непустое → `exact`; migrated unknown не получает массовую плашку); старые derived rows удаляются после успешного cutover;
- API и frontend атомарно через orchestrator; sidecar digest в атомарный release при изменении его контракта (sect §4.4, house, контрольные времена §4.7);
- новый frontend и API деплоятся как один новый контракт; старый frontend/API не
  держится параллельно как compatibility path. Rollback выполняется на прежний
  OCI release целиком, а не смешением старых и новых payload shapes;
- app rollback ≠ schema rollback (prod-orchestrator §:53);
- **protected-data denylist**: users, profiles, access ledger, payments, subscriptions, EveningCheckin, DayFeedback, paid reports;
- **allowlist** destructive cleanup: только derived Today/cache/semantic/history;
- migration compatibility test: старый app на новой additive schema;
- pre-cleanup dump + restore rehearsal на dev-хосте.

## 12. Контрольные вопросы (приёмка модели)

1. Один физический факт считается ровно один раз?
2. Может ли фон создать/усилить/соединить convergence? (нет — вне групп)
3. Может ли неизвестный фактор попасть в work? (нет — исключается)
4. Могут ли одновременно показаться две независимые сферы? (да, до трёх)
5. Чем quiet_day с 0 импульсов отличается от «спокойного дня»? (только нейтральный детерминированный контекст)
6. Может ли LLM изменить числовую истину? (нет — валидатор + null)
7. Меняется ли результат только через явную версию formula/canon? (да)
8. Заморожен ли день после публикации? (да — published immutable, lineage через supersedes)
9. Может ли лунный (даже мажорный) или край-орбисный фактор создать hero? (нет — кроме явных structural lunar event classes из канона)
10. Подтверждены ли частоты C1 re-run'ом новым классификатором, включая страты? (да — committed ablation-отчёт W1)
11. Может ли где-то в системе появиться условное полуденное время или секта из номера дома? (нет — §4.4, fixtures 7–9)
12. Считаются ли метрики только по публичным units? (да — §9)
13. Генерируем ли ночью payload для всех пользователей? (нет — только cohort §5.4; dormant по запросу)
14. Переносим ли старые frontend/API contracts в новый envelope? (нет — Git-архив и W9 cleanup, без dual-read/dual-write)

## 13. Порядок работ (волны)

- **W0 — закрыта этим документом (v1.12).**
- **W1 — FROZEN:** machine-readable canon (§4.3.1 + §4.7: поля evidence-единицы, трёхуровневая eligibility, driver/horizon-правила, rare/structural классы, hero target types, bucket-границы и каноническая сетка + oracle-гейт, event_class пороги, ORB fail-closed, DayDelta identity, sphere mapping и проекция §4.5, геометрическая sect §4.4, fan-out, direct relation); theme registry; коэффициенты evidence; truth tables T1–T5 machine-readable; копирайт-канон; полная C1-схема; исправленный harness re-run (§9), расчётные mutation fixtures 1–5, birth-time fixtures 8–11, sphere semantic-delta attestation, version/parity/sect gates. Fixtures 6/7/12/13 закрываются владельцами runtime-слоёв W2/W6/W3, а не имитируются в W1.
  **Критерий W1 выполнен:** machine-readable canon + исправленный re-run (новый классификатор, дамп → sweep → C1 → страты) + sect-fix в движке + sparse-oracle gate зелёный + расчётная mutation suite + sphere semantic-delta attestation + согласованные state/content/API truth tables. Полный evidence — `analysis/W1_FREEZE_DELTA_ATTESTATION.md`.
- **W2 — deterministic pipeline:** начинается только с Gate 0 в `04_W2_W3_RUNTIME_CONTRACT_TZ.md` §8.1 (noon-fallback и legacy contract isolation); затем canonical event ID, fail-closed house, пятислойная модель, birth-time robustness, группы, polarity/evidence, выбор, DayDelta contract.
- **W3 — persistence:** snapshot (§6), canonical_input_ref, check-in (additive), profile contract (§4.7); persistence/lineage contract — `04_W2_W3_RUNTIME_CONTRACT_TZ.md`.
- **W4 — replay harness как постоянный инструмент** + расширенный корпусный отчёт.
- **W5 — API endpoint + wiring:** consumer matrix, календарный бюджет, local-date фикс, **двухступенчатый pregen по §5.4** (cohort → deterministic snapshot → selective LLM warm-up), calendar/yesterday + typed pregen outcomes/retry/telemetry, single-flight lease, SLO; operations contract — `05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`.
- **W6 — LLM-слой:** один компактный вызов, claim binding, capability-gated validation, null-path.
- **W7 — frontend + contracts + e2e:** начинается с замены legacy Today-fixtures по `03_W7_FRONTEND_DESIGN_TZ.md` §14; только новый envelope (convergence/quiet/unavailable × exact/bucket/unknown × dayTone), статический навигатор, onboarding-режимы, calendar, yesterday/check-in recap; старые frontend contracts/fixtures не переносятся.
- **W8 — атомарный cutover** (§11, `05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`).
- **W9 — после стабильности:** удаление оставшегося недостижимого legacy runtime/adapters по gate §10, затем destructive cleanup derived rows по §11; fixtures и public generated roots к этому моменту уже отсутствуют.
- **W10 — через 60–90 дней:** валидация и ablation по §14.

Каждая волна регистрирует модули/gates в `grace/verification-matrix.md`; per-file тесты — через `owned_tests`.

## 14. Метрики через 60–90 дней (snapshot-linked check-in)

- **selected-sphere hit/coverage:** доля check-in с совпадением observed-сфер и выбранных моделью;
- **copy resonance:** «попал / частично / мимо» — метрика резонанса, не эпистемической истины;
- **polarity:** только weak label для однозначных комбинаций тегов, НЕ ground truth;
- **time agreement:** `not measured` в v1;
- **product:** check-in rate, retention, DAU/MAU (ориентир a16z: 25/40/50%);
- **coverage:** фактический hero rate и impulse-распределение против гипотез §9 (по режимам exact/bucket/unknown раздельно).

## 15. Non-goals

- отдельный экран/retention-copy для «пустого дня» (no_signal как UX упразднён);
- push-уведомления и opt-in UI (отдельный master после cutover);
- аудит расчётного движка через несколько генераторов натальных карт;
- per-sphere матрица observed polarity×intensity в check-in;
- snapshot linkage для Telegram DayFeedback (отдельный срез);
- `low` как публичный evidence level;
- переименование `evidence_level` → `confidence` до живой валидации;
- текстовый fallback любого вида;
- подбор порогов под квоту частоты hero;
- публичное обещание «точное время даёт в N раз больше hero» (одна карта, один сезон);
- ежедневные вердикты 12 сфер в любом виде (D8);
- удаление «лишних» сырых параметров расчёта — они нужны аудиту и replay (§4.1);
- точное rectification (восстановление времени рождения) как продуктовая фича — не входит в rewrite.

## 16. Экраны (компоновка v1, норматив для W7)

Первый экран дня:

```text
Дата → [hero «Что сошлось сегодня» | quiet: «Импульсы дня» / «Главное событие дня»]
     → Импульсы дня (1–3, если не главный блок)
     → Завтра факторы сходятся… (optional; только из frozen snapshot завтра)
     → Контекст периода ▸
     → Сферы жизни (12 статических тайлов, D8)
     → Как это рассчитано ▸
     → дисклеймер
```

Слово «сошлось» встречается только в `convergence_today` (D7). Tense — янтарный (D4). Убрано: DaySummaryCard, «Полный разбор дня», «Почему так у меня» (D10). Отдельного экрана «пустого дня» нет (D1).

**Варианты по режиму времени рождения (§4.7):**

- `bucket`/`unknown`: вместо часов — часть суток («во второй половине дня») или только дата; дома/ASC/лоты не показываются нигде, включая drilldown и страницу сферы; плашка-напоминание (один раз, dismissible): «Время рождения не указано: точные часы и дома не показываем. Уточнить →».
- `unknown` + нет персонально устойчивого: quiet_day с маркером «Общий фон дня» (`personal: false`) — детерминированные факты неба, честно маркированные как НЕ персональный прогноз; строка «Персонального схождения без точного времени сегодня не видно. Уточнить →».
- страница сферы при bucket/unknown: слой 1 строится только из устойчивых натальных фактов (знаки/межпланетные аспекты; дома скрыты с честной пометкой); слой 2 — только устойчивые длинные темы.
- onboarding: три режима (точно HH:MM / примерно — выбор из 4 bucket'ов / не знаю) со спокойной подписью «Покажем только то, что не зависит от точных минут рождения. Время можно уточнить позже».
- переход unknown → exact: спокойное подтверждение «Время уточнено — с завтрашнего дня разбор с домами и точными часами»; прошлые дни не переписываются.

Страница сферы (тап по тайлу) — два слоя с разной частотой обновления:

1. **«В твоей карте» (натал, не меняется):** разбор сферы из натальной карты; LLM один раз, кэш по profile_hash, пересчёт только при смене данных рождения; claim-binding к натальным фактам.
2. **«Сейчас действует» (длинные темы, редко):** детерминированный period context сферы с датой окончания; обновляется при смене периода; без дневной polarity.

Запрещено (review-gate): слова «сегодня»/«завтра» на странице сферы, дневные вердикты и чипы, «освежение» натального текста ради новизны, шаблон-заглушки (нет контента → честный статус «Разбор сферы готовится», 21_TZ §6.6).

Drilldown выбранной сферы (тап по маркированному тайлу, hero- или вторичной строке) — D10.

Calendar-чип: точка = был hero; без точки = опубликованный обычный день; пустой
контур = день не рассчитан. Цветных заливок старой valence нет. Check-in hint:
«Вчера: сошлось в работе» / «Вчера: N импульса» — из snapshot вчерашнего дня,
не из dayStatus.

## 17. Downstream implementation pack (post-freeze)

W1-формула, canon, corpus baseline и replay fingerprint этой редакцией не
изменяются. Для реализации обязательны три производных документа:

1. `04_W2_W3_RUNTIME_CONTRACT_TZ.md` — единственный новый wire-контракт,
   local-date/profile semantics, snapshot persistence и check-in linkage.
2. `05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md` — cohort nightly pregen, LLM lease,
   latency/capacity gates, real E2E, atomic cutover и rollback.
3. `03_W7_FRONTEND_DESIGN_TZ.md` — presentation, responsive layout,
   accessibility и публичный DOM/test contract.

Порядок разрешения расхождений: W1 calculation truth и machine-readable canon
не переопределяются downstream-документами; runtime-форма берётся из `04`,
операционное выполнение — из `05`, presentation/DOM — из `03`. Legacy-код и
старые payload shapes не являются нормативом и не получают compatibility path.

Первый implementation checkpoint: generated contract + state-matrix fixtures +
additive migration + local-date/profile tests. До его зелёной приёмки frontend
не фиксирует собственный ручной shape.
