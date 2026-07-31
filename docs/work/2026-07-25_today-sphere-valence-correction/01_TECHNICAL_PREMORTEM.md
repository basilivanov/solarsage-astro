# Technical Pre-Mortem: Today sphere valence correction

Дата: 2026-07-25. Анализ выполнен до реализации по production evidence SHA
`9d0211fe` и нормативному [`00_TZ.md`](./00_TZ.md).

## 1. Summary

```text
Technical Pre-Mortem: salience/valence split for Today, Calendar and horizons
Affected: ~20 runtime/canon/generated/test files / ≥5 contracts / DB schema: no
Reversibility: feature flag + immutable app rollback; old/new caches coexist
Risks: 11 Tigers (blocking: 11) · 3 Paper Tigers · 4 Elephants
Verdict: GO WITH CONDITIONS for implementation
         NO-GO for production selection until shadow/rollback gates pass
```

Предполагаемый провал после релиза: календарь стал разноцветнее, но один и тот
же день показывает разные статусы в Today и Calendar, часть напряжённых сфер
осталась зелёной из-за пропущенных duplicates, а horizon selector неожиданно
выбрал другие якоря. Rollback вернул старый SHA, но новый cache продолжил
читаться старым кодом. Все эти симптомы предотвращаются только общей factor
identity, versioned cache family и no-drift tests — локальной заменой thresholds
в `verdict_for_score` проблему не закрыть.

## 2. Blast radius

### Что меняется

- API factor canonicalization/deduplication;
- signed day/product-sphere valence и family reducer;
- `ScoringV2Result` integration и day status;
- `ConcreteAdviceRow`/`TodayV2Audit` wire contract;
- общий technical→product mapping canon;
- horizon tone input;
- Today/Calendar cache identity и version family;
- generated OpenAPI/TypeScript/Zod;
- audit/oracle/metrics/verification matrix.

### Что зависит

- `/api/day/{date}` и Today UI;
- `/api/calendar` и mood icon;
- `TodayInterpretationService` и LLM advice context;
- `HorizonSelectionService`, `HorizonToneService`, guidance/claim validator;
- любые consumers `day_status`, включая будущий election-personal flow;
- `TodayPayloadCache`, `SemanticLayerCache` и rollback compatibility;
- mock/real e2e, production audit scripts и golden fixtures.

### Что shared

- normalized day signals и `ActivationLayer`;
- `spheres.v1.yml`, `activation_rules.v1.yml`, aspect rules;
- Today/Calendar runtime selection flags;
- shared generated contracts;
- production API/sidecar/frontend immutable release SHA;
- PostgreSQL cache rows разных scoring identities.

Sidecar astronomy и DB schema не меняются.

## 3. Risk registry

| # | Failure scenario (symptom) | Class | Urgency | Blast radius | Detection | Mitigation |
|---|---|---|---|---|---|---|
| T1 | Один transit остаётся и signal, и activation; scores всё ещё завышены | 🐅 Correctness | merge-blocking | day, 12 spheres | duplicate trap + factor hash | canonical semantic key, activation wins |
| T2 | Dedup склеивает два разных контакта; реальное напряжение исчезает | 🐅 Correctness | merge-blocking | verdict/status | collision fixtures | typed tuple identity, fail closed |
| T3 | Family decay зависит от input order или даёт по три слота каждой polarity | 🐅 Correctness | merge-blocking | status/spheres | permutation/metamorphic tests | one stable ranking per family |
| T4 | Today selected 2.1, Calendar читает 2.0 cache; иконки расходятся | 🐅 Contract/cache | merge-blocking | Today/Calendar | mismatch metric + parity test | one request-scoped identity resolver |
| T5 | Перенос mapping canon меняет sphere ranks и выбранные horizon IDs | 🐅 Regression | merge-blocking | all horizons | no-drift golden | preserve salience mapping values, diff gate |
| T6 | LLM/frontend начинает вычислять или перезаписывать verdict | 🐅 Contract | merge-blocking | user advice | request spy + generated contract | numeric truth only in API engine |
| T7 | New cache воспринимается old SHA как current после rollback | 🐅 Operations | merge-blocking | production rollback | two-SHA rehearsal | version pair in cache hash, old rows retained |
| T8 | Shadow выглядит зелёным, но на production corpus почти всё становится caution/avoid | 🐅 Product reliability | merge-blocking | calendar/user trust | 7-day/replay distribution diff | shadow review, no instant activation |
| E1 | Нет доказанного semantic-key parity signal↔activation для всех transit types | 🐘 Assumption | decision blocker | dedup | pre-flight fixture inventory | confirm four required mappings |
| E2 | Family decay `[1,.5,.25]` ещё не подтверждён владельцем продукта | 🐘 Product canon | decision blocker | all valence | owner decision record | freeze in canon before code |
| E3 | Thresholds good/caution/avoid не откалиброваны на corpus | 🐘 Product canon | decision blocker | 12 spheres | replay report | owner review; no target color quota |
| E4 | Команда может пытаться «починить плоский календарь» заданной долей цветов | 🐘 Objective | decision blocker | correctness | review of acceptance criteria | forbid target distribution as truth |
| P1 | Новый pure reducer заметно увеличит API latency | 🐯 Performance | observation | `/day`, calendar miss | benchmark/p95 | bounded factors, no extra network |
| P2 | Новые JSON fields потребуют тяжёлую DB migration | 🐯 Data | observation | deploy | schema inspection | Text JSON + existing version columns; no migration |
| P3 | Sidecar regression изменит астрономию | 🐯 Coupling | observation | all facts | request/body diff | no sidecar code or request change |
| A1 | Implementer меняет знак `final_score` вместо добавления valence | 🐅 Agent error | merge-blocking | horizon selection | no-drift tests | preserve legacy salience contract |
| A2 | Implementer считает day status голосованием 12 rows/трёх horizons | 🐅 Agent error | merge-blocking | calendar icon | architecture test/import trap | global ledger only |
| A3 | Implementer копирует mapping/thresholds в несколько модулей | 🐅 Maintainability | merge-blocking | future drift | source grep/canon tests | one typed canon loader |

Tigers A1–A3 — обязательные implementer-agent scenarios: они выделены отдельно,
чтобы code review не пропустил типичную «быструю починку» не того слоя.

## 4. Merge-blocking Tigers

### T1/T2 — cross-source identity ошибается в любую сторону

- **Symptom:** high salience остаётся раздутой либо значимый аспект пропадает.
- **Mechanism:** `AstroSignal` не имеет готового общего ID с sidecar activation;
  строковая эвристика по display title легко даёт miss/collision.
- **Detection:** property fixtures для t2n/t2a/t2l/house; audit duplicate/collision
  counts; ledger hash до/после permutation.
- **Pre-flight:** выписать реальные пары полей обоих контрактов и доказать
  semantic key на production-shaped fixtures.
- **Test:** один physical transit в двух sources даёт один factor; разные target
  type/key никогда не сливаются.
- **Mitigation:** typed tuple builder, activation priority, invalid key fail-closed.

### T3 — family reducer сам создаёт bias

- **Symptom:** перестановка входа меняет цвет; supportive и tense получают по
  три полных места и снова сходятся к steady.
- **Mechanism:** отдельные lists по polarity или нестабильный sort нарушают
  единый budget family.
- **Detection:** permutation, fourth-factor and polarity-competition traps.
- **Pre-flight:** owner принимает один общий rank и `[1,.5,.25,0…]`.
- **Test:** все permutations byte-equal; четвёртый weaker factor не влияет;
  stronger factor детерминированно вытесняет третий.
- **Mitigation:** один pure reducer, stable factor ID tie-break, один canon.

### T4 — Today/Calendar split-brain

- **Symptom:** Today показывает `tense`, календарь `steady` для той же даты.
- **Mechanism:** два сервиса resolve flags/cache key в разное время или Calendar
  принимает semantic row старой identity.
- **Detection:** `today_calendar_status_mismatch_total`, API integration parity.
- **Pre-flight:** один immutable request selection value до любого cache read.
- **Test:** matrix old/new flags × Today/Calendar × cache hit/miss/rollback.
- **Mitigation:** общий identity resolver; Calendar не импортирует formula.

### T5/A1 — исправление verdict ломает horizon selection

- **Symptom:** long/medium/fast activation IDs меняются без изменения астрономии.
- **Mechanism:** implementer делает `final_score` signed или меняет shared mapping
  weights во время переноса canon.
- **Detection:** canary no-drift snapshot selected IDs/timing/impact.
- **Pre-flight:** сохранить текущий mapping и salience outputs как baseline.
- **Test:** legacy `SphereScoreV2.final_score` и selection byte-equal на fixture.
- **Mitigation:** отдельный `ProductSphereAssessment`; selector читает salience.

### T6/A2/A3 — contract ownership drift

- **Symptom:** backend verdict один, UI/LLM показывает другой; будущая правка
  thresholds обновляет не все копии.
- **Mechanism:** ручные TS types, prompt-derived status или duplicated constants.
- **Detection:** `pnpm contracts:check`, import/source grep, LLM response mutation
  trap.
- **Pre-flight:** Pydantic roots и один canon loader в module map.
- **Test:** LLM invalid/mutated verdict ignored; frontend receives generated field;
  grep запрещает threshold literals вне canon/tests.
- **Mitigation:** API numeric truth, generated wire, frontend presentation only.

### T7 — rollback читает несовместимый cache

- **Symptom:** после orchestrator rollback старый API 500/показывает new semantics.
- **Mechanism:** new rows имеют тот же cache identity или previous/current pair
  обновлён неатомарно.
- **Detection:** Release A→B→A rehearsal с сохранёнными rows обеих версий.
- **Pre-flight:** prove cache hash differs solely by reviewed version fields.
- **Test:** old SHA ignores 2.1; new SHA выбирает 2.1; rollback снова читает 2.0.
- **Mitigation:** scoring/payload/frontend/content bump; rows не удалять.

### T8 — семантически честная формула всё равно плохо откалибрована

- **Symptom:** календарь перестаёт быть плоским, но становится почти весь красным;
  пользователи теряют доверие.
- **Mechanism:** thresholds/family decay выбраны по одному canary, а не corpus.
- **Detection:** shadow diff по дням/profiles; status/verdict histograms.
- **Pre-flight:** sanitized replay corpus и owner review без желаемой квоты цветов.
- **Test:** synthetic truth traps + replay report; replay не заменяет unit oracle.
- **Mitigation:** Release A shadow минимум 7 дней или эквивалентный corpus;
  activation только после sign-off.

## 5. Rollback plan

1. Release A поставляет dual-run и contract compatibility, selection остаётся 2.0.
2. Release B выбирает 2.1 только после recorded previous SHA=Release A.
3. Incident: выключить `TODAY_VALENCE_V1_ENABLED` через operator-controlled
   immutable release/env procedure; не редактировать container filesystem.
4. Выполнить canonical `prod-orchestrator rollback <release-a-sha>
   --manual-confirm`.
5. Оставить 2.1 cache rows: old SHA не видит их из-за versioned hash.
6. Проверить одну дату в Today и Calendar, status parity и cache identity.
7. Проверить legacy horizon IDs и отсутствие `today_calendar_status_mismatch`.

DB downgrade и удаление данных не нужны. Целевой RTO ≤15 минут. Если old SHA
может прочитать 2.1 row как current, rollout получает NO-GO независимо от тестов
формулы.

## 6. Pre-flight checklist

- [ ] Owner утвердил `[1.0, 0.5, 0.25]` family decay.
- [ ] Owner утвердил thresholds `0.75/1.30/1.50/2.00`.
- [ ] Signal↔activation semantic keys доказаны для t2n/t2a/t2l/house.
- [ ] Production-shaped fixtures не содержат birth data/username/UUID.
- [ ] Сохранён no-drift horizon baseline для двух canaries.
- [ ] Новый canon — единственный technical→product mapping source.
- [ ] Pydantic roots и exact generated consumers перечислены.
- [ ] Today/Calendar используют один request-scoped identity resolver.
- [ ] Dual-run logs/metrics добавлены в registry до использования.
- [ ] Independent valence oracle не импортирует production reducer.
- [ ] Two-SHA cache/rollback test написан до Release B.
- [ ] Shadow corpus/report формат согласован; target color quota отсутствует.
- [ ] GRACE contracts/owned_tests/verification matrix обновлены.

## 7. Verdict

**GO WITH CONDITIONS для начала реализации**, только после закрытия четырёх
Elephants E1–E4 решениями из pre-flight.

**NO-GO для merge**, пока не доказаны T1–T7 tests/contracts/no-drift.

**NO-GO для production selection**, пока Release A shadow не показал приемлемые
semantic diffs, Today/Calendar parity и отрепетированный rollback. Изменение
threshold `score >= 6` без factor ledger, cache/version и horizon gates считается
не исправлением, а запрещённым partial hotfix.
