# [HISTORICAL PRE-FIX SNAPSHOT] SolarSage Independent Audit: Basil, 2026-07-08

> **NOTE**: This document describes the historical pre-fix state of the SolarSage TodayPayload and calculates the baseline mismatches before Wave W0 trust fixes were applied.
> Post-W0 fixes have resolved these mismatches (including retrograde flags, Moon phase rounding, and day/natal signal separation).
> Please refer to the numbered canonical artifacts under `artifacts/audit/2026-07-08/` for the current post-fix audit results.

Дата аудита: 2026-07-08
Пользователь: `basil_ivanov`, `eb3876be-e1b4-43d6-b887-1f8554e33150`
Production target: `2026-07-08 12:00 Europe/Moscow`
Артефакты: `artifacts/audit/2026-07-08/`

## Executive summary

Production `TodayPayload` для Basil на 2026-07-08 имеет `day_status=supportive`, UI summary "Поддерживающий день" и status line "День возможностей". Это подтверждается независимым scoring oracle: production и oracle совпали по `day_status`, всем `sphere_scores`, `top_signals` с точностью `0.00`.

Почему день стал поддерживающим: сумма позитивных аспектов, прошедших threshold, равна `7.3468`; сумма напряжённых равна `4.9252`; ratio `1.4917` больше production-порога `1.3`. Главные позитивные факторы: `Transit_Pluto trine Saturn`, `Transit_Sun trine Mercury`, `Transit_Uranus trine Saturn`, `Transit_Mercury trine Uranus`, `Transit_Saturn trine Mars`, `Transit_Mars trine Saturn`, `Transit_Moon trine Neptune`. Главные напряжённые факторы тоже есть, но их меньше: `Transit_Neptune opposition Saturn`, `Transit_Moon opposition Pluto`, `Transit_Mercury square Pluto`.

Astronomical oracle подтвердил транзитные долготы и дома транзитных планет. Найдены mismatches: raw `retrograde=false` неверен для `Mercury`, `Neptune`, `Pluto`; UI Moon phase `46%` расходится с Swiss-формулой `43.792%`; "Moon opposite Pluto" в UI является `Transit_Moon opposite natal Pluto` с орбом `1.0454°`, не `Transit_Moon opposite Transit_Pluto` (там орб `101.3532°`, аспекта нет).

Главный gap к `docs/14_SolarSage_scoring_rewrite_TZ.md`: doc-14 v2 фактически не внедрён. Есть canon YAML и куски кода, но `activation_layer` отсутствует в ответе, `activation_rules.v1.yml` не потребляется, convergence в этом кейсе равен нулю (`n=1` для всех планет/домов), версии в payload остаются `scoring_version=1`, `activation_layer_version=null`, `scoring_canon_version=null`.

## Trace map: production TodayPayload path

| Step | File | Function | What happens |
|---|---|---|---|
| API route | `apps/api/app/api/day.py` | `get_day` | Parses `date_str`, checks session/profile/access, calls `TodayService.get_today_payload`. |
| Today service | `apps/api/app/services/today_service.py` | `TodayService.get_today_payload` | Main production pipeline and cache boundary. |
| Natal context | `apps/api/app/services/natal_context_service.py` | `get_or_build_natal_context` | Gets cached natal context; calls sidecar `/v1/natal` only on cache miss. |
| SolarSage client | `apps/api/app/clients/solarsage_client.py` | `get_transits` | Calls sidecar `/v1/transits` for `12:00` in profile timezone. |
| Sidecar transits | `apps/solarsage/solarsage/api/transits.py` | `post_transits` | Direct Swiss Ephemeris positions via `calculate_positions`. |
| Normalization | `apps/api/app/services/normalization_service.py` | `normalize_day` | Builds natal signals, transit-to-natal aspects, transit planet-in-natal-house signals. |
| Day filter | `apps/api/app/services/day_scoring_signals.py` | `filter_day_scored_signals` | Keeps `Transit_*` day signals, removes static natal signals from scoring. |
| Delta layer | `apps/api/app/services/day_delta_service.py` | `compute_deltas` | Adds `delta_kind`, `phase`, `daily_salience` by comparing 2026-07-07. |
| Scoring | `apps/api/app/services/scoring_service.py` | `score_day` | Computes `sphere_scores`, `day_status`, `top_signals`. |
| Semantic | `apps/api/app/services/semantic_service.py` | `build_semantic_layer`, `build_why_contexts` | Builds deterministic contexts for LLM. |
| LLM | `apps/api/app/services/llm_service.py` | `generate_*` | Generates headline, reading, notes, Why sections. Final text was read from production cache. |
| UI advice | `apps/api/app/services/today_interpretation_service.py` | `build` | Builds `day_summary` and `concrete_advice` evidence rows. |
| Frontend fetch | `app/(grace)/day/[date]/page.tsx` | `DayPage` | `useDay(dateStr)` then `adaptTodayPayload`. |
| Frontend adapter | `lib/adapters/today-payload.ts` | `adaptTodayPayload` | Preserves API headline/dayStatus/topFlags/daySummary/concreteAdvice. |
| UI render | `components/today/today-screen.tsx` | `TodayScreen` | Renders `DaySummaryCard`, `ConcreteDayAdvice`, `DayReading`, `WhyExpanded`. |

## Critical findings

1. **Doc-14 v2 scoring is not production-complete.** `activation_layer` is missing, `activation_rules.v1.yml` is dead data, convergence has no real multi-technique source, and payload version fields are not v2.

2. **Raw retrograde flags are wrong.** Sidecar `Planet` schema has no `retrograde`; API schema defaults `retrograde=false`. Oracle shows Mercury, Neptune, Pluto are retrograde by speed on 2026-07-08. UI `motion` partly recovers this from speed, but raw contract is false.

3. **Moon phase percentage is approximate and fails oracle tolerance.** Production says `Убывающая Луна 46%`; direct Swiss formula gives `43.792%`. The mismatch comes from a triangular elongation formula in `TodayInterpretationService.build`, not the standard illumination formula.

4. **Why contexts mix static natal house signals into day explanations.** `SemanticService.build_why_contexts` receives `signals` (all signals), not just `day_signals`; sections `period_background` and `manifestation_zones` cite houses `5, 2, 5` from natal placements as if they were today/fon manifestations. Actual transit houses are Sun/Mercury 1, Moon/Saturn/Neptune 10, Venus/Jupiter 2, Mars/Uranus 12, Pluto 8.

5. **LLM practical advice contradicts product evidence in one place.** Why section 9 says "Общайся с близкими для улучшения отношений", while product row `relationships` is `avoid` with evidence `Moon opposition Pluto`.

## Calculation mismatches

| Check | Result |
|---|---|
| Transit longitudes Sun through Pluto | PASS. Delta `0.0°` for all 10 planets against direct `pyswisseph`. |
| Transit signs | PASS for all 10 planets. |
| House placement for transiting planets | PASS under `WHOLE_SIGN`. |
| Retrograde flags | FAIL for Mercury, Neptune, Pluto. Speeds are negative, production raw `retrograde=false`. |
| Moon phase | FAIL. Oracle `43.792%`, production `46%`, delta `-2.208` percentage points. |
| Moon opposite Pluto | Clarification: Transit Moon opposite natal Pluto PASS, orb `1.0454°`. Transit Moon opposite transit Pluto FAIL, orb from opposition `101.3532°`. |
| Natal planet houses | Incomplete. `raw_natal_context.planets[*].house` is `None`; houses are inferred later via cusp lookup. |

## Scoring mismatches

No mismatches against current production scoring.

| Output | Production | Independent oracle | Status |
|---|---:|---:|---|
| day_status | supportive | supportive | PASS |
| crisis_transformation_control | 5.26 | 5.26 | PASS |
| inner_background_unconscious | 4.45 | 4.45 | PASS |
| body_energy_health | 3.79 | 3.79 | PASS |
| work_status_achievement | 3.46 | 3.46 | PASS |
| money_security_resources | 2.54 | 2.54 | PASS |
| home_family_roots | 1.97 | 1.97 | PASS |
| thinking_speech_learning | 1.42 | 1.42 | PASS |
| relationships_partnership | 0.89 | 0.89 | PASS |
| meaning_expansion_vector | 0.46 | 0.46 | PASS |

Top signals also match:

1. `Transit_Moon opposition Pluto`, orb `1.0454`, strength `0.8693`, `new_today`.
2. `Transit_Mars sextile Moon`, orb `0.7876`, strength `0.8687`, `stronger_than_yesterday`.
3. `Transit_Moon trine Neptune`, orb `2.5315`, strength `0.6836`, `new_today`.
4. `Transit_Mars trine Saturn`, orb `2.0645`, strength `0.7419`, `weaker_than_yesterday`.
5. `Transit_Sun in 1 house`, strength `1.0`, `background`.

## Why the visible statuses happened

### Why the day is supportive

Production status logic uses aspect polarity only. It does not use `sphere_scores` directly for `day_status`.

Positive score: `7.3468`
Negative score: `4.9252`
Threshold: `positive > negative * 1.3` and `positive >= 1.0`
Actual: `7.3468 > 6.4028`, so `supportive`.

### Why "Документы" are green

`documents` has no direct backend sphere score in the current canon output. It becomes `good` through product evidence fallback in `TodayInterpretationService.build`: `Saturn` is associated with `documents`, and the row finds `Transit_Mars trine Saturn`, orb `2.0645°`, strength `0.7419`. Soft aspect -> `good`.

This is supported, but it is not coming from a `legal_affairs` or `partnerships_contracts` sphere score because those sphere keys are not present in `grace/canon/spheres.v1.yml`.

### Why "Отношения" are red

`relationships_partnership` score is `0.89`. `verdict_for_score()` maps `score <= 2.0` to `avoid`. The row then finds compatible tense evidence: `Transit_Moon opposition Pluto`, orb `1.0454°`, strength `0.8693`. Therefore `relationships=avoid` is supported.

### First six product rows

| Row | Verdict | Evidence | Supported |
|---|---|---|---|
| Работа | caution | `Transit_Neptune opposition Saturn`, orb `0.2923`, strength `0.9635`; work score `3.46` maps to caution | yes |
| Деньги | caution | `Transit_Venus square Uranus`, orb `3.7621`, strength `0.4626`; money score `2.54` maps to caution | yes |
| Документы | good | `Transit_Mars trine Saturn`, orb `2.0645`, strength `0.7419` | yes, but via fallback planet mapping, not sphere score |
| Отношения | avoid | relationships score `0.89` plus `Transit_Moon opposition Pluto` | yes |
| Спорт | neutral | body/energy score `3.79` maps to neutral; evidence `Transit_Mars in 12 house` | partial, text about goals is generic |
| Общение | avoid | thinking/speech score `1.42` plus `Transit_Mercury square Pluto`, orb `1.2906`, strength `0.8156` | yes |

## Missing techniques vs docs/14

| Requirement from docs/14 | Status | Evidence |
|---|---|---|
| `derived.activation_layer` with by_planet/by_house/by_lot | missing | No activation layer artifact in sidecar/API response; `TodayPayload.activation_evidence=None`. |
| Minimum 7 activation techniques | missing | Signals have `technique=null`, `technique_family=null`; no profection/firdar/SR/SA/progression/lot/angle/eclipse signals. |
| `activation_rules.v1.yml` consumed | dead code/data | File exists, but grep shows no production loader/consumer. |
| Convergence bonus from independent techniques | partial/dead in this case | `_compute_convergence` exists, but all counts are `1`; bonus is zero. |
| Convergence technique families | partial | YAML has families; signals do not carry techniques, so families never matter. |
| Threshold instead of top-40 | partial | API scoring uses threshold, but on `base = aspect_weight * strength`, not doc-14 `score_hint`; sidecar monolith still contains ranked `score_hint` logic outside Today path. |
| Anti-dominance | partial | Cap exists, but no `dominance_capped` output, no auditability, and no DoD test for flag. |
| Canonized spheres/aspects/dignities | partial | YAML files exist and scoring reads spheres/aspects; `dignities` loader exists but condition factor is not used in day scoring. No jsonschema fail-loud loader. |
| Versioning | missing | Payload meta has `scoring_version=1`, `activation_layer_version=null`, `scoring_canon_version=null`; doc requires string versions like `ss-scoring-2.0`, `al-1.0`. |
| DoD tests | mostly missing | Current tests cover basic scoring and top-signal velocity, not doc-14 activation/convergence/anti-dominance/version/golden snapshot requirements. |

## Untested behavior

- No regression test that `derived.activation_layer` exists and contains at least 7 doc-14 techniques.
- No convergence test proving `thinking_speech_learning.salience` increases `>= 1.4x` and `<= 2.0x`.
- No anti-dominance test asserting share `<= 0.65` and `dominance_capped == true`.
- No exact threshold test for `score_hint=0.34` excluded and `0.36` included.
- No version invalidation test proving `activation_layer_version` changes do not invalidate natal chart hash but do invalidate semantic/today caches.
- No v2 golden snapshot for Basil/Vasiliy with fixed `sphere_scores ±0.02`.
- No test that raw retrograde flags match speed-derived retrograde.
- No test that Moon phase percent uses astronomical illumination formula.
- No test that `WhyThisHappens` contexts use day-scored signals for day manifestation zones instead of static natal house signals.
- No test that concrete advice cannot contradict another row verdict, e.g. relationship advice inside practical bullets when relationships are `avoid`.

## LLM unsupported claims

| UI text area | Claim | Evidence result |
|---|---|---|
| Headline | "поддержку в глубоких чувствах и творческих порывах" | partial. Supportive status is proven; "deep feelings" is supported by Pluto/Moon/inner-background scores; "creative impulses" relies on static 5th-house/natal context rather than day-scored transit evidence. |
| Day summary | "Поддерживающий день", "День возможностей" | supported by `day_status=supportive`. |
| Day summary fact | "Луна оппозиция Плутон" | supported only as transit Moon opposite natal Pluto, not transit Pluto. UI label hides that distinction. |
| Reading | "Секспектиль Марса с Луной" | supported signal is `Transit_Mars sextile natal Moon`; text has typo and should be "секстиль". |
| Reading | "Солнце в твоем первом доме" | supported by final day chart and house oracle. |
| Notes | "финансы и отношения сейчас не так важны" | weak/partial. Money score is rank 5 with caution; relationships rank 8/avoid. "Not important" is not the same as "caution/avoid". |
| Why #4 | "длительные транзиты... дома 5 и 2" | unsupported as day evidence. Those houses come from static natal `planet_in_house` signals included in `all_signals`, not from day-scored transit house placements. |
| Why #7 | "5 дом творчества... 2 дом денег..." | unsupported as current-day manifestation for the same reason. |
| Why #9 | "Общайся с близкими для улучшения отношений" | unsupported/contradicts `relationships=avoid` with `Moon opposition Pluto`. |

## Recommended fixes

1. Implement real `activation_layer` as a separate deterministic artifact before scoring. Populate `AstroSignal.technique` / `technique_family`, and expose a cacheable `activation_layer_version`.

2. Move convergence calculation to the activation layer, not inferred from generic `signal.type`. Count canonical technique families and write explainable human evidence.

3. Fix sidecar planet output to include `retrograde = speed < 0` and, ideally, `planet.house` for natal/transit contexts where coordinates/house system are known.

4. Replace the Moon phase calculation in `TodayInterpretationService.build` with standard illumination: `(1 - cos(moon_lon - sun_lon)) / 2 * 100`.

5. Change `SemanticService.build_why_contexts` to separate `all_signals`, `day_signals`, and natal context. Period/manifestation sections must not label static natal houses as today/fon evidence.

6. Make product advice internally consistent. If `relationships=avoid`, practical bullets should not recommend relationship outreach unless the evidence explicitly supports a safe version of that action.

7. Version payloads per docs/14: set `scoring_version`, `activation_layer_version`, `canon_versions`; use these versions for today/semantic cache invalidation.

8. Add audit artifacts to CI for at least one fixed production-like user/date using deterministic LLM-off fixtures.

## Tests to add

- `apps/api/tests/test_activation_layer.py`: build activation layer for fixture and assert by_planet/by_house/by_lot with at least 7 techniques.
- `apps/api/tests/test_scoring_convergence.py`: Mercury/profection/Saturn transit fixture with expected salience boost and cap.
- `apps/api/tests/test_scoring_threshold.py`: exact `score_hint` threshold inclusion/exclusion.
- `apps/api/tests/test_scoring_versioning.py`: cache invalidation when scoring/activation/canon versions change.
- `apps/api/tests/test_astronomy_oracle.py`: retrograde flags and Moon phase formula for 2026-07-08.
- `apps/api/tests/test_semantic_contexts.py`: `manifestation_zones` uses day-scored transit houses, not static natal planet-in-house rows.
- `apps/api/tests/test_today_concrete_advice_consistency.py`: practical bullets cannot contradict concrete row verdicts.
- `apps/api/tests/test_basil_2026_07_08_golden.py`: fixed snapshot asserting day_status, top_signals, sphere_scores, concrete rows, Moon phase, retrogrades.

## Exact files/functions to change

- `apps/solarsage/solarsage/schemas/natal.py`: `Planet` - add `retrograde`.
- `apps/solarsage/solarsage/utils/ephemeris.py`: `calculate_positions` - set `retrograde = speed_lon < 0`.
- `apps/solarsage/solarsage/api/transits.py`: `post_transits` - preserve retrograde in response.
- `apps/solarsage/solarsage/api/natal.py`: `post_natal` - preserve retrograde and add planet house if implemented.
- `apps/api/app/schemas/natal.py`: `SolarSageTransitPlanet`, `SolarSagePlanetPosition` - stop masking missing retrograde as false; validate or preserve explicit value.
- `apps/api/app/services/today_interpretation_service.py`: `build` - replace Moon phase formula and add row-level consistency guard.
- `apps/api/app/services/semantic_service.py`: `build_why_contexts` - pass/use separate day-scored signals for daily/manifestation contexts.
- `apps/api/app/services/normalization_service.py`: `normalize_day` - attach `technique="transit_to_natal"` / `technique_family="transit"` and add future activation-layer inputs.
- `apps/api/app/services/scoring_service.py`: replace inferred `_compute_convergence` with activation-layer based convergence; emit `dominance_capped`.
- `apps/api/app/services/today_service.py`: set doc-14 versions in `TodayMeta`, persist activation evidence/period context, include version keys in cache invalidation.
- `apps/api/app/schemas/today.py`: make v2 version fields explicit and add activation-layer/evidence contracts if wire contract changes.
- `grace/canon/*.v1.yml`: add jsonschema validation and use `activation_rules.v1.yml` in production.
- `lib/adapters/today-payload.ts`: preserve any new evidence fields needed by UI tests, without client-side astrology.

## Audit tooling added

- `scripts/audit_today.py`: production collector. Example:
  `apps/api/.venv/bin/python scripts/audit_today.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out artifacts/audit/2026-07-08`
- `scripts/audit_scoring_oracle.py`: independent scoring oracle. It reads `grace/canon/*.yml` and `signal_trace.csv`; it does not import `ScoringService`.
- `scripts/audit_astronomy_oracle.py`: independent direct `pyswisseph` oracle; it does not import `solarsage.*` or `app.*`.
- `scripts/test_audit_scoring_oracle.py`: unit coverage for the independent scoring oracle.

Key generated artifacts:

- `artifacts/audit/2026-07-08/input_profile.json`
- `artifacts/audit/2026-07-08/raw_natal_context.json`
- `artifacts/audit/2026-07-08/raw_transits.json`
- `artifacts/audit/2026-07-08/signal_trace.csv`
- `artifacts/audit/2026-07-08/day_scored_signals_after_filter.csv`
- `artifacts/audit/2026-07-08/scoring_intermediate_table.csv`
- `artifacts/audit/2026-07-08/sphere_scores.csv`
- `artifacts/audit/2026-07-08/top_signals.csv`
- `artifacts/audit/2026-07-08/semantic_layer.json`
- `artifacts/audit/2026-07-08/why_contexts.json`
- `artifacts/audit/2026-07-08/final_today_payload.json`
- `artifacts/audit/2026-07-08/scoring_oracle_comparison.json`
- `artifacts/audit/2026-07-08/astronomy_oracle_summary.json`
