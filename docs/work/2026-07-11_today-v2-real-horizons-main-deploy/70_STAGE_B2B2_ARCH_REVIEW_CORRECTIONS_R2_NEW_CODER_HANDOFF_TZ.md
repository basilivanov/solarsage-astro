# Stage B2B2 — architect review corrections R2 / new coder handoff

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Accepted HEAD/origin: `c47863a0c4b2be2242c276bb610a262b4b91a737`  
Parent documents:

- `68_STAGE_B2B2_DETERMINISTIC_GUIDANCE_CLAIMS_COVERAGE_TZ.md`;
- `69_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R1_TZ.md`.

Статус: **NOT ACCEPTED — CONTINUE CURRENT UNTRACKED B2B2 WORK, NO COMMIT/PUSH**

## 0. Для нового coding executor

Ты продолжаешь работу предыдущего кодера в той же рабочей директории. Не
откатывай и не удаляй текущие untracked B2B2-файлы. Сначала полностью прочитай
документы `68`, `69` и затем этот документ `70`.

Документ `69` остаётся полным нормативным ТЗ. Этот документ:

- передаёт фактическое состояние новому кодеру;
- фиксирует независимо воспроизведённые остаточные blockers после R1;
- уточняет, что именно делать дальше;
- заменяет ошибочный callback предыдущего исполнителя.

Если формулировка здесь короче, чем в `69`, исполняй более строгую и полную
формулировку из `69`. Ничего не додумывай и не расширяй scope.

## 1. Режим и запреты

Ты — coding executor. Архитектор не пишет product/test code и примет результат
только после независимого review.

Запрещено:

- использовать субагентов;
- `git add`;
- commit;
- push;
- checkout/reset/clean/stash текущих B2B2-файлов;
- начинать B3, B4, B5 или release/deploy;
- менять accepted B1/B2A/B2B1 files;
- менять public/generated contracts;
- менять Today/Semantic/Calendar/frontend/sidecar integration;
- менять selection thresholds, scoring, content canon, auth, production API;
- добавлять LLM, cache, settings, telemetry или runtime fixture path;
- трогать unrelated user files.

Неприкосновенные unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Индекс должен оставаться пустым. После callback остановись.

## 2. Принятый контекст до B2B2

Уже приняты и запушены:

```text
B1   3a58c581bbe010e98e78b2295a135f138d32bd88
     feat(today): add grounded three-horizon contract

B2A  cd27d1a8056eef92737e992c1b0998423331734b
     feat(today): add deterministic horizon selection

B2B1 c47863a0c4b2be2242c276bb610a262b4b91a737
     feat(today): add grounded horizon content pipeline
```

Текущий `HEAD` и `origin/preview/...` оба стоят на B2B1. B2B2 ещё не принят и
не закоммичен.

Известный exact full-API baseline до B5 — только эти шесть failures:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

Не исправляй их в B2B2 и не допускай новых failures.

## 3. Текущий B2B2 allowlist

Продолжать можно только в этих текущих untracked code/test/fixture files:

```text
apps/api/app/schemas/horizon_guidance.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/tests/_horizon_guidance_testkit.py
apps/api/tests/fixtures/horizon_guidance_coverage.v1.yml
apps/api/tests/test_horizon_guidance_formatter.py
apps/api/tests/test_horizon_guidance_service.py
apps/api/tests/test_horizon_claim_validator.py
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_pipeline_benchmark.py
```

Не создавай дополнительные production/test files. Разрешённые split modules
`horizon_guidance_builders.py` и `horizon_claim_policy.py` уже созданы.

Документы `68`, `69`, `70` принадлежат architect work record. Не переписывай
их и не включай их содержание в product code.

## 4. Фактическое состояние после предыдущего кодера

Предыдущий callback сообщил `READY_STAGE_B2B2_R1_REVIEW`, но он не подтверждает
acceptance. Независимый architect run 2026-07-12 дал следующее.

### 4.1 Focused tests

```text
92 passed in 0.98s
```

Это означает только отсутствие текущих test failures. Ниже доказано, что часть
тестов является false proof и принимает невалидные данные.

### 4.2 GRACE фактически FAIL

Реальный запуск `scripts/grace_lint.py` на всех 12 code/test Python files:

```text
grace_lint: FAIL — 109 violation(s) across 12 file(s)
```

Предыдущий callback `grace: PASS 6 production files` неверен по двум причинам:

- проверена только часть allowlist;
- production helpers/properties и почти все public test functions всё ещё без
  парных function contracts.

Required final result:

```text
grace_lint: PASS — 12 file(s) checked
```

Не скрывать нарушения, не исключать test files, не менять lint script.

### 4.3 Size gate фактически FAIL

Текущие line counts:

```text
schema                         214
formatter                      517
builders                       474
policy                         530
guidance service               321
validator                      289
testkit                        453
formatter tests                309
guidance tests                 459
claim validator tests          786   <-- FAIL, required <=700
coverage tests                 267
benchmark tests                142
```

`test_horizon_claim_validator.py` уже больше лимита и после добавления GRACE
contracts станет ещё больше. Не удаляй требуемые проверки. Сожми его через
табличные/parametrized mutation cases и вынеси только общие builders в уже
разрешённый `_horizon_guidance_testkit.py`. Итог каждого test file `<=700`.

### 4.4 Coverage печатает 60/60, но не использует даты/timezones

Текущий output:

```text
total=60
selected=60
contract_ready=60
guidance_valid=60
coverage=100.0%
dates=12/12
timezones=5/5
```

Это ложноположительный результат. Внутри loop сейчас находится:

```py
# Use shifted_story_for to get selection with actual date/tz
selection, layer, scoring = build_selected_story(story)
```

То есть `target_date` и `timezone` только добавляются в `set`, но не участвуют
ни в selection, ни в timing, ни в guidance. Импортированный
`shifted_story_for` не вызывается.

Прямые architect probes текущего `shifted_story_for`:

```text
2028-02-29 America/New_York structure_boundaries_control -> missing_medium
2026-03-29 Europe/Berlin communication_learning_documents -> missing_medium
2026-07-08 Europe/Moscow relationships_values_closeness -> missing_medium
```

Следовательно реальная coverage сейчас не существует.

### 4.5 Claim validator всё ещё fail-open

Architect сохранил sibling items и мутировал ровно одно поле. Текущий validator
принял все 18 invalid mutations:

```text
duplicate_evidence
intro_eyebrow
intro_headline
intro_body
horizon_id
horizon_eyebrow
horizon_title
horizon_summary
horizon_plain_explanation
horizon_plain_explanation_with_invented_date
strength_public_id
manifestation_safe_arbitrary_body
manifestation_safe_arbitrary_condition
manifestation_profile_provenance
technique_safe_arbitrary_why
technique_nested_timing_label
technique_why_with_invented_date
action_profile_provenance
```

Это не Pydantic boundary issue. Все 18 дошли до
`HorizonClaimValidator.validate()` и вернулись без exception.

Текущие mutation tests маскируют проблему. Например manifestation mutation
передаёт только один элемент вместо исходного полного списка и поэтому
получает `manifestation_invalid` из-за count mismatch, а не из-за изменённого
body/title. Такие тесты не засчитываются.

Также текущие тесты прямо объявляют некоторые invalid mutations допустимыми:

```text
"Eyebrow is cosmetic and not validated"
"Headline is cosmetic and not validated"
"Item id is cosmetic and not validated"
"Item title is cosmetic and not validated"
"Duplicate evidence is not rejected"
```

Это противоречит exact deterministic contract из `69` и должно быть удалено.

### 4.6 Четыре первоначальных architect probes теперь fail-closed

Эти исправления сохранить:

```text
changed_state_and_labels     -> timing_alignment_invalid
unsupported_strength_text    -> fact_provenance_invalid
invented_manifestation_body  -> unsupported_life_claim
embedded_snake_case          -> internal_copy_leak
```

Они не заменяют 18 residual probes и полную mutation matrix.

### 4.7 Benchmark частично исправлен, но доказательство неполное

Текущий реальный output:

```text
horizon_pipeline_benchmark: p95=22.95ms runs=20 combinations=1728
```

Timed body теперь включает нужные stages. Это сохранить. Остаточные проблемы:

- builder docstring говорит, что проверяет exact `12/12/12`, но не проверяет;
- test не asserts exact 120 activation count and 40/40/40 families;
- warmup/measured loops не assert `combinations_evaluated == 1728` на каждом
  run;
- final output совпал с 1728 случайно/фактически, но regression gate отсутствует.

### 4.8 Formatter в основном исправлен, но sanitization неполна

Сохранить уже работающие date/instant/timezone/human-copy fixes. Дополнительно
убрать raw input из `HorizonGuidanceError` path/item_id. Сейчас unknown
planet/angle/house/source/entity/theme/technique values могут попасть в
exception через `item_id=<raw key>` или `target_type=<raw value>`.

Error text допускает только stable code + structural path + заранее безопасный
opaque index. Не включать raw activation ID, fact ID, theme key, entity key,
sentinel, user/profile value или исходную строку.

Добавить отдельные sanitization tests с sentinel raw keys и exact assertion,
что sentinel отсутствует в `str(exc)`.

## 5. Что делать дальше — точный порядок

### Step 1 — прочитать нормативные документы и сохранить scope

Полностью прочитать `68`, `69`, `70`. Затем проверить:

```bash
git status --short --branch
git diff --cached --quiet
```

Не делать reset/clean. Не менять accepted files.

### Step 2 — исправить GRACE на полном allowlist

Сразу довести структуру всех 12 Python files до реального GRACE PASS:

- accurate `AI_HEADER`;
- paired `START_MODULE_CONTRACT` / `END_MODULE_CONTRACT`;
- accurate `START_MODULE_MAP` / `END_MODULE_MAP`;
- paired contract у каждого public/nontrivial function, method and property,
  который требует lint;
- contracts у public pytest functions или parametrized public entrypoint;
- accurate module maps after test parametrization;
- no fake event names; `emitted_logs: none` здесь корректен.

Не откладывать GRACE до конца: line limits нужно контролировать одновременно.

### Step 3 — сделать validator exact и fail-closed

Validator обязан независимо получить expected deterministic values из:

```text
context
loaded canons
formatter
shared pure builders
activation evidence
```

Не считать generator output доверенным. Не импортировать
`HorizonGuidanceService` в validator как единственный oracle. Разрешено и
предпочтительно вынести pure expected-copy helpers в уже существующий
`horizon_guidance_builders.py`, чтобы generator и validator вызывали одинаково
детерминированные typed builders.

Required exact checks:

1. Evidence:
   - activation evidence IDs unique;
   - every selected activation exists exactly once;
   - duplicate evidence rejects exact code `evidence_duplicate`.

2. Intro:
   - exact eyebrow;
   - exact headline;
   - exact body;
   - exact theme key;
   - exact ordered activation IDs;
   - mutation code `intro_alignment_invalid`.

3. Horizon shell:
   - exact `id == horizon.<long|medium|fast>`;
   - exact horizon order;
   - exact eyebrow/title/summary/plain explanation;
   - exact activation IDs, tone, likely spheres;
   - code `horizon_alignment_invalid`, except tone/sphere use their existing
     dedicated codes.

4. Timing:
   - recompute full `HorizonTimingPresentation`;
   - compare complete public timing model, including state and every label;
   - compare actions valid-until raw and label;
   - compare complete nested technique timing model, including labels/state;
   - every single timing mutation reaches `timing_alignment_invalid` or
     `technique_invalid`, not generic public cross-reference first.

5. Strength/risk:
   - exact deterministic selected ranked unused fact per horizon/kind;
   - exact public ID `claim.<horizon>.<fact id>`;
   - exact kind/text/conditional/provenance;
   - natal/profile/sphere/activation lists exact;
   - lower-ranked otherwise-valid replacement rejects;
   - no fact reuse;
   - safe arbitrary ID/text/provenance rejects.

6. Manifestations:
   - rebuild expected full ordered list using canon + formatter;
   - exact count/order/id/title/condition/body/sphere/provenance;
   - natal/profile provenance must be empty;
   - safe arbitrary condition/body must reject `manifestation_invalid`.

7. Actions:
   - rebuild expected full ordered `do` and `avoid` lists;
   - exact heading/count/order/id/kind/text/conditional/provenance;
   - activation/natal/profile/sphere provenance exact;
   - no subset/reorder/extra otherwise-valid canonical action accepted;
   - safety class must exist;
   - tone/verdict/intent/forbidden-intent-pair gates retained;
   - exact codes from `69`.

8. Technique:
   - rebuild exact single technique explanation;
   - exact technique/label/what/why/full timing/activation IDs;
   - safe arbitrary `why_it_matters_now` rejects `technique_invalid`;
   - invented date inside technique copy cannot pass.

9. Warnings/schema/guidance mode:
   - exact schema version and deterministic mode remain enforced by typed
     public model;
   - deterministic B2B2 output warnings must equal exact expected empty list;
   - do not silently accept arbitrary warnings.

Validation order must prove the named rule:

- first sanitize/scan forbidden, unsupported, internal leakage and invented
  numbers across all user-visible fields;
- then exact deterministic alignment;
- then public evidence cross-reference as defense in depth;
- do not let an unrelated count mismatch or canonical action mismatch make a
  mutation test green.

If a malformed object cannot safely reach a later layer, map it to a sanitized
specific `HorizonClaimValidationError`; never expose raw Pydantic/input body.

### Step 4 — complete policy scans

Build one iterator over every user-visible string and use it consistently.
It must include at least:

```text
intro eyebrow/headline/body
horizon eyebrow/title/summary/plain explanation
horizon timing range/peak/state labels
manifestation title/condition/body
strength/risk text
actions heading/valid-until label/do/avoid text
technique label/what/why
technique nested timing range/peak/state labels
```

Rules:

- forbidden certainty/high-stakes fragments apply everywhere;
- unsupported employer/partner/debt/diagnosis/event assertions apply
  everywhere except the narrow exact conditional scenario allowance from
  `69`;
- raw `Transit_`/`Natal_`, activation IDs, fact IDs, sentinels and embedded
  snake_case reject everywhere;
- invented numeric tokens outside exact canonical/timing output reject;
- plain explanation and technique copy are not exempt.

### Step 5 — replace false mutation tests with a real matrix

Use a validated baseline and mutate exactly one independent field while
preserving all siblings, list counts and unrelated values.

Required test shape:

- table/parametrization is preferred to stay under 700 lines;
- each case records `name`, mutation builder and exact expected code;
- no no-op mutation such as `UTC -> UTC`;
- no test saying deterministic copy is cosmetic;
- no broad `ValueError` for claim-validator cases;
- no test may pass merely because a sibling list was accidentally dropped;
- count only cases that actually expect and receive rejection;
- final claim-specific invalid mutation count `>=40`;
- all rejected by their intended exact code.

The matrix from section 10.4 of `69` is mandatory. Additionally encode all 18
architect residual probes from section 4.5 here as explicit regressions.

Add a test helper assertion that confirms the mutated path differs from
baseline while all declared unrelated sibling paths remain unchanged where
practical.

### Step 6 — make YAML coverage real

#### 6.1 Strict fixture loader

`build_coverage_cases()` is the only Python entrypoint for the corpus. It must
strict-load the YAML through test-only Pydantic models:

- extra forbid;
- exact schema version;
- exact 5 profiles and 12 dates;
- unique IDs/dates;
- exact accepted profile ID set;
- valid IANA timezones;
- known story/natal/verdict cases;
- exact accepted date set including DST boundaries and leap day.

No duplicated hardcoded profile/date metadata in `test_horizon_coverage.py`.

#### 6.2 Fix `shifted_story_for`

Use actual local aware datetimes for the supplied case:

```text
target_date = YAML date
target_time = 12:00
target_tz   = YAML IANA timezone
```

Build/shift every relevant activation, including distractors:

- long: local calendar-year date range, `exact_at=None`;
- medium: target local noon ±90 days, exact target local noon;
- fast: target local day start/end, exact target local noon;
- convert instant boundaries to explicit UTC `Z` values;
- preserve eligibility/classification and story convergence;
- never leave fixed 2026-07-12/UTC timing.

Return a result shape exposing selection/reason/diagnostics. Do not assert null
selection inside helper before coverage can count/report it.

Direct regression cases must pass:

```text
2028-02-29 America/New_York structure_boundaries_control
2026-03-29 Europe/Berlin communication_learning_documents
2026-07-08 Europe/Moscow relationships_values_closeness
```

Assert their raw UTC values differ where timezone/DST requires it and their
public local labels resolve to the requested local date/noon.

#### 6.3 Full 60-case loop

For every YAML case use its real date/timezone/story/natal/verdict through:

```text
selection
contract-ready checks
fact pack
tone
HorizonGuidanceContext
guidance build
claim validator
public cross-reference
TodayV2HorizonsBlock JSON roundtrip
second build byte identity
```

Also assert every selected activation belongs to that exact case layer,
boundaries are complete, medium/fast exacts exist, provenance is complete and
impact threshold is met.

The test must fail if `build_selected_story` is substituted for
`shifted_story_for`. Add an explicit assertion per case:

```text
layer.target_date == case.date
layer.target_tz == case.timezone
selection timing target_local/target_utc correspond to that case
```

Print exact actual counters:

```text
coverage: <valid>/60 <percent>
coverage_selected: <selected>/60
coverage_contract_ready: <ready>/<selected>
coverage_dates_timezones: 12 DATES / 5 TIMEZONES
coverage_failure_breakdown: <exact dict>
```

Do not equate `1 passed` pytest count with coverage case count.

### Step 7 — finish benchmark proof

Keep fixture/service construction outside timed body. Keep full six-stage
pipeline inside every warmup/measured run.

Add exact assertions:

- `len(layer.activations) == 120`;
- input groups exactly 40 long-capable / 40 medium-capable / 40 fast-capable;
- B2A bounded candidate counts exactly 12/12/12 if diagnostics expose them;
- `combinations_evaluated == 1728` in each of 3 warmups;
- `combinations_evaluated == 1728` in each of 20 measured runs;
- every run returns a valid deterministic block;
- exact 3 warmups and 20 measured samples;
- p95 exact index and `<100ms`.

Print exactly:

```text
horizon_pipeline_benchmark: p95=<ms> runs=20 combinations=1728
```

### Step 8 — sanitized errors

Audit every `HorizonGuidanceError` and `HorizonClaimValidationError` creation in
the allowlist. Error strings may contain only:

- closed stable code;
- structural path such as `items[0].timing`;
- safe closed horizon label/index.

Remove raw values currently passed through `item_id` or interpolated paths:

```text
activation IDs
fact IDs
theme keys
planet/angle/lot/entity keys
source keys
target_type values
raw template/body/input strings
sentinels/profile data
```

Tests inject unique sentinels and assert exact absence from `str(exc)`.

## 6. Mandatory gates

Run from `/opt/solarsage-astro` unless command says otherwise.

### 6.1 Focused

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q
```

Then separately capture evidence:

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_coverage.py -q -s

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_pipeline_benchmark.py -q -s
```

### 6.2 Upstream regression

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_ordering.py \
  apps/api/tests/test_horizon_selection_benchmark.py \
  apps/api/tests/test_personal_fact_pack_service.py \
  apps/api/tests/test_horizon_tone_service.py -q
```

### 6.3 GRACE — exact full list

```bash
python3 scripts/grace_lint.py \
  apps/api/app/schemas/horizon_guidance.py \
  apps/api/app/services/horizon_guidance_formatter.py \
  apps/api/app/services/horizon_guidance_builders.py \
  apps/api/app/services/horizon_guidance_service.py \
  apps/api/app/services/horizon_claim_policy.py \
  apps/api/app/services/horizon_claim_validator.py \
  apps/api/tests/_horizon_guidance_testkit.py \
  apps/api/tests/test_horizon_guidance_formatter.py \
  apps/api/tests/test_horizon_guidance_service.py \
  apps/api/tests/test_horizon_claim_validator.py \
  apps/api/tests/test_horizon_coverage.py \
  apps/api/tests/test_horizon_pipeline_benchmark.py
```

Required exact result: PASS on all 12 files, zero violations.

### 6.4 Contracts and full API

```bash
pnpm contracts:check
apps/api/.venv/bin/python -m pytest apps/api/tests -q
```

Full API may contain only the six known baseline IDs from section 2. No new
failure, collection error, warning-as-error or import error.

### 6.5 Static/final

```bash
git diff --check
git diff --cached --quiet
```

Additionally:

- scan all allowlist files for trailing whitespace, including untracked files;
- production files `<=650` lines;
- validator `<=400`;
- guidance service `<=350`;
- each test file `<=700`;
- no production line `>140` chars;
- exact allowlist only;
- unrelated paths untouched;
- index empty;
- no commit/push.

Remember: ordinary `git diff --check` does not inspect untracked files, so run
an explicit whitespace scan over the allowlist.

## 7. Required independent evidence before callback

Before reporting READY, explicitly run and include results for:

1. All 18 residual fail-open probes from section 4.5 — `18/18 REJECT`.
2. Original 4 architect probes — `4/4 REJECT` with exact codes.
3. Real claim mutation matrix — `>=40`, every case rejected by intended code.
4. Three direct shifted-story regression cases — all selected/contract-ready.
5. Real coverage — actual `valid/60`, not pytest test count.
6. Benchmark — all 23 runs observed `1728` combinations.
7. GRACE — exact full 12-file command, zero violations.
8. Error-sanitization sentinel matrix — no sentinel in any exception string.

Do not write PASS based on inspection. Every line must come from an executed
gate.

## 8. Callback

Return exactly one compact callback after all requirements pass:

```text
READY_STAGE_B2B2_R2_REVIEW
changed_paths: <exact code/test/fixture paths>
accepted_head_unchanged: c47863a0c4b2be2242c276bb610a262b4b91a737
production_split: PASS <all production line counts>
test_sizes: PASS <all test line counts <=700>
grace: PASS 12/12 ZERO_VIOLATIONS
timing_formatter: PASS <exact cases>
valid_until_human_copy: PASS <long/medium/fast samples>
sanitized_errors: PASS <sentinel cases>
residual_fail_open_probes: 18/18 REJECT
architect_original_probes: 4/4 REJECT <exact codes>
claim_mutations: <rejected>/<total> REJECT_BY_INTENDED_CODE
unsupported_claims: ZERO
privacy_sentinels: PASS
shifted_story_regressions: 3/3 PASS
coverage_yaml_source: PASS_STRICT
coverage: <valid>/60 <percent>
coverage_selected: <n>/60
coverage_contract_ready: <n>/<selected>
coverage_dates_timezones: 12 DATES / 5 TIMEZONES
coverage_failure_breakdown: <exact>
pipeline_benchmark: p95=<ms> runs=20 combinations=1728 all_runs=23/23
focused_tests: <result>
upstream_regression: <result>
contracts: PASS_NO_PUBLIC_DIFF
api_full: <result + exact six baseline IDs>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_stage: NOT_STARTED
```

Если хотя бы один пункт не проходит, не возвращай READY. Исправь только внутри
allowlist и повтори gates. После callback остановись и жди architect review.
