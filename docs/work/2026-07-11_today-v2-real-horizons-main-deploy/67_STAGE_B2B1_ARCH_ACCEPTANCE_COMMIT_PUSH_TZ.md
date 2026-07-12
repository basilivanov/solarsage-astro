# Stage B2B1 — architect acceptance and exact commit/push

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Base HEAD/origin: `cd27d1a8056eef92737e992c1b0998423331734b`  
Родительские ТЗ: `63_...`, `64_...`, `65_...`, `66_...`  
Статус: **ARCHITECT ACCEPTED — COMMIT/PUSH ONLY**

## 0. Режим выполнения

Это не новая реализационная волна. Не менять production-код, canons, tests или
copy. Выполнить только точный scoped commit и push уже принятого B2B1.

Запрещено:

- входить в B2B2;
- исправлять шесть известных baseline failures;
- форматировать или редактировать файлы;
- добавлять в index что-либо вне allowlist;
- использовать `git add .`, `git add -A` или широкие glob-паттерны;
- трогать preview-процессы на `3003`/`18092`;
- трогать production systemd/nginx/порты;
- делать merge/rebase/reset/cherry-pick.

## 1. Основание acceptance

Архитектор независимо подтвердил:

```text
production pattern content duplication: ZERO
pattern order: self-describing 1..12
original invalid mutations: 11/11 REJECT
empty/only-personal/missing-long/missing-medium/missing-fast fact packs: REJECT
activation id 161 chars: REJECT
activation id 160 chars with aligned provenance: ACCEPT
impossible tone provenance mutations: REJECT
valid zero sphere component states: ACCEPT
action templates: 86 unique
action safety coverage: 480/480
focused B2B1: 110 passed
GRACE: PASS
production schema line limits: PASS
contracts: PASS_NO_PUBLIC_DIFF
full API: 6 failed, 1041 passed, 5 skipped, 1 warning
index before commit: EMPTY
local HEAD == origin branch: cd27d1a8056eef92737e992c1b0998423331734b
```

Ровно шесть известных baseline failures:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

Они не созданы B2B1 и не входят в эту commit-only операцию.

## 2. Exact commit allowlist

Добавить в index только следующие 24 файла:

```text
grace/canon/horizon_language.ru.v1.yml
grace/canon/horizon_actions.ru.v1.yml
grace/canon/personal_patterns.ru.v1.yml

apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/horizon_content_canon_types.py
apps/api/app/schemas/personal_fact_pack.py
apps/api/app/schemas/horizon_tone.py

apps/api/app/services/canon_service.py
apps/api/app/services/horizon_content_canon_service.py
apps/api/app/services/personal_fact_pack_service.py
apps/api/app/services/horizon_tone_service.py

apps/api/tests/_horizon_content_testkit.py
apps/api/tests/test_canon_service.py
apps/api/tests/test_horizon_content_canon_service.py
apps/api/tests/test_horizon_language_canon.py
apps/api/tests/test_horizon_actions_canon.py
apps/api/tests/test_personal_patterns_canon.py
apps/api/tests/test_personal_fact_pack_service.py
apps/api/tests/test_horizon_tone_service.py

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/63_STAGE_B2B_DECOMPOSITION_AND_INVARIANTS.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/64_STAGE_B2B1_CONTENT_CANONS_FACT_PACK_TONE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/65_STAGE_B2B1_ARCH_REVIEW_CORRECTIONS_R1_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/66_STAGE_B2B1_ARCH_REVIEW_CORRECTIONS_R2_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/67_STAGE_B2B1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

## 3. Unrelated paths — must remain untracked/untouched

Ни один из этих путей не должен попасть в index или commit:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 4. Exact procedure

1. Убедиться, что текущая ветка точная:

```bash
git branch --show-current
```

Ожидается:

```text
preview/solarsage-v2-human-first-navigator-ux
```

2. Убедиться, что до staging index пустой:

```bash
test -z "$(git diff --cached --name-only)"
```

3. Выполнить `git add --` только с точным перечнем из section 2. Не использовать
`.` / `-A` / директории целиком.

4. Получить отсортированный staged path list:

```bash
git diff --cached --name-only | LC_ALL=C sort
```

Сверить его с section 2: ровно 24 файла, ни одного лишнего и ни одного
пропущенного.

5. Проверить staged diff:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached -- apps/api/app/services/canon_service.py apps/api/tests/test_canon_service.py
```

Для новых файлов дополнительно просмотреть `git diff --cached --stat` и первые
заголовки staged diff. Не редактировать принятую реализацию.

6. Отдельно доказать отсутствие unrelated paths в index:

```bash
for path in \
  .grace \
  artifacts/design \
  docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md \
  grace.db \
  skills
do
  test -z "$(git diff --cached --name-only -- "$path")" || exit 1
done
```

7. Создать ровно один commit с exact message:

```text
feat(today): add grounded horizon content pipeline
```

8. Push только текущую preview-ветку:

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
```

9. После push проверить:

```bash
test -z "$(git diff --cached --name-only)"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux)"
git status --short
```

После commit ожидается, что `git status --short` показывает только заранее
существовавшие unrelated untracked paths из section 3.

## 5. Callback

Вернуть и остановиться:

```text
READY_STAGE_B2B1_COMMITTED_PUSHED
branch: preview/solarsage-v2-human-first-navigator-ux
commit: <sha>
message: feat(today): add grounded horizon content pipeline
staged_paths_before_commit: 24 EXACT_ALLOWLIST
unrelated_in_commit: ZERO
push: PASS
local_equals_origin: PASS
index_after_commit: EMPTY
remaining_status: <exact git status --short>
code_changes_after_acceptance: ZERO
next_stage: NOT_STARTED
```

После callback ничего больше не делать.
