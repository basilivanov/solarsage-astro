# W4-CANARY TZ: обезличенные TodayFocus fixtures и безопасный audit

Дата: 2026-07-28  
Phase / Wave: **W4-TODAY-CONVERGENCE**, reusable canary contract  
Родители: `21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md`,
`27_TZ_W4_AMENDMENT_PUBLIC_EVENT_SELECTION.md`  
Потребители: B2.1 selector, C2 narrative boundary, O1 cache/pregen, F1 frontend  
Роль: backend/test coder + reviewer. Ничего не коммитить и не пушить — коммит
делает ревьюер.

## 1. Цель

Создать один reusable canary слой, который доказывает выбор событий,
provenance, локальное время и failure states без Telegram-auth, production DB,
sidecar или реального LLM в CI.

Live audit остаётся финальным smoke, но не является test fixture. Тесты
начинаются с минимального обезличенного `TodayFactor` ledger и не хранят
полный пользовательский `/api/day` payload.

## 2. Обнаруженная privacy-проблема

Текущий `scripts/audit_day_contract.py --freeze` заявлен как sanitized, но
фактически выполняет `json.dump(d)` всего response. Make target также имеет
default реального Telegram ID. Такой файл нельзя считать обезличенным canary:
он содержит большой персональный производный payload и может случайно попасть
в git/artifacts.

До реализации safe exporter:

- не использовать `--freeze` для нового TodayFocus canary;
- не коммитить full live response;
- не использовать username/TG ID/UUID в имени case или JSON;
- существующие legacy full-day fixtures не копировать как основу.

## 3. Два уровня fixtures

### 3.1. Factor fixture — backend oracle

Каталог:

```text
apps/api/tests/fixtures/today_focus/factors/
```

Содержит только вход pure builder и deterministic expected output. Никакого
LLM-copy и полного Today payload.

Нормативный top-level allowlist:

```json
{
  "fixtureVersion": "today-focus-factor.v1",
  "caseId": "convergence-20260728-a",
  "targetDate": "2026-07-28",
  "timezone": "Europe/Moscow",
  "factors": [],
  "valenceAssessments": {},
  "expected": {}
}
```

Каждый `factors[]` содержит только поля `TodayFactor`:

```json
{
  "factorId": "act:t2n__MOON__SQUARE__PLUTO",
  "activationIds": ["t2n__MOON__SQUARE__PLUTO"],
  "technique": "transit_to_natal",
  "techniqueFamily": "transit",
  "sourceKey": "MOON",
  "targetKey": "PLUTO",
  "targetType": "natal_planet",
  "aspectType": "square",
  "themeKeys": ["PLUTO"],
  "productSpheres": ["work", "decisions"],
  "polarity": "tense",
  "strength": 0.72,
  "salience": 0.72,
  "activeFrom": null,
  "exactAt": "2026-07-28T10:31:00Z",
  "activeUntil": null,
  "phase": "exact",
  "temporalRole": "anchor_today"
}
```

Допустимы только values, необходимые выбранному кейсу. Запрещены birth
coordinates/date/time, natal chart целиком, profile, person name, username,
Telegram/user/session IDs, prompt, provider response и raw sidecar body.

`valenceAssessments` содержит только product sphere key и публично нужные
`verdict/confidence`; никаких evidence texts или персональных score dumps.

### 3.2. Public focus fixture — contract/UI oracle

Каталог:

```text
apps/api/tests/fixtures/today_focus/public/
```

Это минимальный public `focus` block + meta identity, нужный contract и
frontend tests. `ready` copy здесь synthetic и явно помечен test-only; нельзя
замораживать текст реального provider ответа. Для failure-case все LLM-owned
поля `null`.

Top-level keys: `fixtureVersion`, `caseId`, `meta`, `focus`. Любые `profile`,
`v2`, `concreteAdvice`, `why`, `reading`, auth/session поля запрещены.

## 4. Expected oracle для 28.07

Case `convergence-20260728-a`, Europe/Moscow, после B2.1 обязан выбрать:

| Display | UTC instant | `event.id` | `sourceActivationIds` | Relation |
|---|---|---|---|---|
| 13:31 | `2026-07-28T10:31:00Z` | `ev:act:t2n__MOON__SQUARE__PLUTO` | `t2n__MOON__SQUARE__PLUTO` | `convergence_event` |
| 18:19 | `2026-07-28T15:19:00Z` | `ev:act:t2n__MOON__SEXTILE__URANUS` | `t2n__MOON__SEXTILE__URANUS` | `independent_event` |
| 19:52 | `2026-07-28T16:52:00Z` | `ev:act:t2n__MARS__OPPOSITION__NEPTUNE` | `t2n__MARS__OPPOSITION__NEPTUNE` | `independent_event` |

Winning convergence theme — Pluto. Moon–Pluto занимает reserved anchor slot;
остальные два события выбраны общим public-event ranking, но не становятся
evidence схождения.

Fixture обязательно содержит и вытесненные candidates, иначе он не доказывает
ranking:

- neutral Moon–Lot Necessity, если canonical title builder уже знает его human
  label; иначе — эквивалентный synthetic neutral factor с поддерживаемым
  target, чтобы в case A он проиграл именно ranking, а не title filter;
- более слабый Moon–Mercury;
- все факторы, нужные для самого Pluto convergence, включая supporting/background
  связь, но без полного профиля.

Отдельный case H содержит тот же тип lot без human mapping и доказывает
eligibility reject независимо от ranking case A.

## 5. Expected oracle для 29.07

Case `convergence-20260729-b`, Europe/Moscow, проверяет вечернюю связку:

```text
19:24 — Луна в напряжении с твоим Солнцем
19:40 — Луна напротив твоей Луны
```

Точные `factorId`, `event.id`, source IDs и UTC instants фиксируются только из
sanitized normalized exporter и затем проходят reviewer check. Их запрещено
угадывать по пользовательскому тексту. Длительный фирдар Солнца допускается
как `background` evidence, но не как третья timed event.

## 6. Обязательный case matrix

| Case | Что доказывает |
|---|---|
| A: convergence 28.07 | reserved winner anchor + two strongest independent exact events |
| B: convergence 29.07 | два вечерних связанных anchor, background firdar не становится event |
| C: single impulse | одна/две несвязанные точные точки, state без «сошлось» |
| D: background only | только годовая/медленная техника, `events=[]`, `not_needed` |
| E: no accent | пустой eligible pool, `events=[]`, `not_needed` |
| F: null time | delta/peak без exact instant: null last, без fake `00:00` |
| G: LLM unavailable | facts сохранены, все LLM fields null, retryable pregen |
| H: title ineligible | неизвестный lot/machine key пропущен с reason, следующий candidate выбран |
| I: DST boundary | local-day gap/fold не дублирует и не теряет event |
| J: family reducer boundary | 4+ factors одной family выявляют расхождение group/valence decay; expected блокируется до owner decision |

Case J — diagnostic gate, а не способ молча изменить ranking. До решения
владельца fixture хранит оба рассчитанных значения и `decisionRequired=true`,
но не утверждает новый winner.

## 7. Safe exporter contract

В отдельном implementation slice добавить в `scripts/audit_day_contract.py`:

```text
--freeze-focus PATH
```

Этот режим:

1. извлекает только allowlisted normalized factors/expected focus;
2. заменяет case identity на случайный/нейтральный `caseId`;
3. удаляет user/profile/auth/provider fields рекурсивно;
4. сортирует keys, factors и expected IDs детерминированно;
5. валидирует output отдельной fixture schema;
6. отказывается писать файл при неизвестном top-level/field key;
7. пишет атомарно и завершает non-zero при invariant/privacy failure.

Добавить отдельный Make target `audit-focus-freeze`, требующий явные `TG_ID` и
`DATE`; никакого default реального пользователя. Генерация auth остаётся live
preflight и никогда не сохраняется в fixture.

Существующий `--freeze`/`audit-day-freeze` должен быть честно переименован в
help как **full payload regression fixture**, не sanitized. Если legacy test
нуждается в нём, output ограничивается test profile или gitignored локальным
artifact; он не используется для W4 canary.

## 8. Exact implementation scope

- `apps/api/tests/fixtures/today_focus/README.md` — schema, privacy allowlist,
  regeneration policy;
- `apps/api/tests/fixtures/today_focus/factors/*.json` — cases A–J;
- `apps/api/tests/fixtures/today_focus/public/*.json` — UI/content states;
- `apps/api/tests/test_today_focus_fixture_canaries.py` — loader, schema,
  builder, permutation, oracle;
- `scripts/audit_day_contract.py` — `--freeze-focus` и sanitized focus section;
- `scripts/contracts/normalize_today_focus_fixture.py` — deterministic
  formatter/check либо расширение существующего normalizer без full payload;
- `Makefile` — explicit `audit-focus-live`/`audit-focus-freeze`, no real-ID
  default;
- privacy tests с denylist и max-size guard.

Не менять selector, title builder, sidecar, LLM prompt или UI в этом срезе.
Fixture выявляет расхождение, но не «чинит» production code.

## 9. Validation rules

Каждый fixture проходит:

1. JSON/schema validation, unique `caseId` и `fixtureVersion`.
2. Top-level/recursive allowlist; denylist для `tg`, `telegram`, `username`,
   `userId`, UUID, birthday, coordinates, initData, cookie, token, profile,
   prompt/response.
3. Max file size, исключающий случайный full payload.
4. Все `expected.events[].sourceActivationIds` существуют в input factors.
5. `event.id` не смешан с activation ID и соответствует wire convention.
6. UTC→IANA local date/time проверены библиотекой, включая DST cases.
7. Input permutation не меняет selected IDs/order/relation.
8. `occursAt=null` остаётся null и сортируется последним.
9. `contentState=unavailable` не содержит ни одного LLM-owned текста.
10. Никакой live LLM/network/Telegram/DB/sidecar call в unit/CI.

## 10. Verification и evidence

После реализации:

```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_today_focus_fixture_canaries.py -q
python -m pytest tests/test_today_focus_builder.py tests/test_today_focus_contract.py -q
cd ../..
python3 scripts/contracts/normalize_today_focus_fixture.py \
  apps/api/tests/fixtures/today_focus --check
```

Reviewer получает список case IDs, privacy scanner result, oracle diff и
sanitized focus-only audit. Full live payload, TG account или birth profile в
evidence запрещены.

## 11. Escalation

Если canary невозможно построить без нового sidecar поля, wire schema change,
raw profile или ручного угадывания IDs/time — стоп. Нужен отдельный контракт,
а не расширение fixture allowlist персональными данными.
