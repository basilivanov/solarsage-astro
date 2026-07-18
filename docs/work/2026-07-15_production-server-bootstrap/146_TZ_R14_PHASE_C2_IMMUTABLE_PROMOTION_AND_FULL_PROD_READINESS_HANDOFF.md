# R14 Phase C2 — immutable promotion (current/previous/rollback/GC) и полная production readiness. Канонический handoff-ТЗ

Это единственный стартовый документ для продолжения работ. Он передаёт полный контекст: что уже принято независимыми review, что сейчас незавершено, какие дефекты известны и в каком порядке их закрывать. Перед началом работ следующий исполнитель обязан полностью прочитать:

- `AGENTS.md`;
- `69_AUDIT_PRODUCTION_READINESS_GAPS.md`;
- `70_TZ_ENV_PROFILES_AND_SECRET_BOUNDARY.md`;
- `73_TZ_CANONICAL_DATABASE_IDENTITY.md`;
- `74_TZ_NONCYCLIC_FRESH_HOST_GITHUB_AND_SSH.md`;
- `77_ARCH_IMMUTABLE_RELEASE_DEPLOY.md`;
- `79_ARCH_GLOBAL_MAINTENANCE_STATE_MACHINE.md`;
- `80_AUDIT_AND_ARCH_EPHEMERIS_PRODUCTION_GATE.md`;
- `81_ARCH_TELEGRAM_BOT_LAUNCH_GATE.md`;
- `136_REVIEW_R14_PHASE_C1A_R7K_ACCEPTED_INDEPENDENT.md`;
- `142_REVIEW_R14_PHASE_C1B1_ACCEPTED_INDEPENDENT.md`;
- `143_TZ_R14_PHASE_C1B2_OPERATIONAL_PROFILE_CONSUMERS.md`;
- `144_REVIEW_R14_PHASE_C1B2_REJECTED_CLI_ORDER.md`;
- `145_TZ_R14_PHASE_C1B2_CORRECTION_CLI_ORDER.md`;
- текущие `scripts/lib/prod-release-promotion.sh`, `scripts/prod-release-promote.sh`, `scripts/tests/test-prod-release-promotion.sh`.

## 1. Цель

Довести ВСЕ подготовительные работы для production до полностью автоматизированного, проверяемого, fail-closed состояния:

- каждый slice имеет изолированный честный harness, зелёный независимо, с mutation self-proof;
- любой destructive переход атомарен либо доказуемо откатывается; промежуточное состояние всегда fail-closed;
- ни один тест не становится зелёным за счёт ослабленных oracle, fallback repo, swallowed restore или production override.

Actual production deploy/promotion/start допускается ТОЛЬКО вручную по явной команде пользователя. На всех подготовительных этапах запрещены:

- реальный deploy, promotion, запуск/остановка production-сервисов;
- restart/reload systemd и nginx;
- миграция или restore реальной БД;
- git commit, git push и любые другие prod mutations.

## 2. Операционные ограничения

- Работать напрямую в интерактивной сессии. Никаких внутренних subagents, Task, explorer, opencode/Kimi-агентов, параллельных делегаций.
- Сохранять грязный worktree и чужие изменения. Запрещены `git checkout`, `git restore`, `git reset` и любые операции, стирающие незакоммиченное.
- Запрещены Ctrl-C по чужим процессам и убийство tmux-сессий/панелей.
- Не писать в файлы chain-of-thought/reasoning comments вида `Wait`, `Let's`, `Ah`, `we can`, `we should` (см. существующий негативный пример: `scripts/tests/test-prod-release-promotion.sh:826-829`).
- Sandbox-тесты никогда не трогают реальные `/opt/solarsage-runtime`, `/run`, `/var/lib`, `systemctl`, `curl`, `git`: все эти цели заменяются подстановками и mock-командами внутри приватного `/tmp`-sandbox.
- Все test substitutions — только по точным fixed anchors с явными pre/post counts: count до подстановки обязан совпасть с ожиданием, count после — ноль для заменяемых anchor'ов; несовпадение — немедленный fail.
- Manual-only prod boundary: любой production effect — отдельная явная команда пользователя после независимой приёмки.
- GRACE contracts/structured logs и правила `AGENTS.md` обязательны для каждого нового или существенно изменённого файла (`AI_HEADER`, `START_MODULE_CONTRACT`, `START_MODULE_MAP`, для нетривиальных функций `START_FUNCTION_CONTRACT`/`START_BLOCK`).

## 3. Каноническая архитектура (AGENTS.md)

- Порты: **5433** PostgreSQL (`solarsage-db`, Docker); **8000** единственный FastAPI (`solarsage-api.service`); **3002** frontend Next.js production (`solarsage-frontend.service`); **18091** SolarSage sidecar (внутренний); **80/443** nginx — единая точка входа (`/api/*` → 8000, остальное → 3002).
- Production auth: только Telegram WebApp → HMAC → `/api/auth/telegram` с реальным `TELEGRAM_BOT_TOKEN`.
- Запрещено: ручной `uvicorn` (фантомный бэкенд без env), порт 8001 как API (это sidecar), `USE_FIXTURES` (удалён), Prefect (удалён).
- Тестирование: `npx vitest run`; `cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q`; Playwright e2e через `scripts/generate-telegram-test-initdata.py`.
- Immutable release layout по `77_ARCH`: `/opt/solarsage-runtime/releases/<40-lowercase-sha>` с `current`/`previous` symlink, root-owned runner резолвит `current` ровно один раз, health обязан возвращать exact full release SHA.
- Global maintenance lock/state по `79_ARCH`: `/run/solarsage-maintenance.lock` (root:astro 0660), durable state в `/var/lib/solarsage/maintenance/`, inherited lease `SOLARSAGE_MAINTENANCE_FD` + `SOLARSAGE_MAINTENANCE_OPERATION_ID`, фазы persist до destructive boundary, `recovery_required` без автоматического продолжения.

## 4. Уже независимо принято — не регрессировать

Принятые файлы не переписывать и не ослаблять без доказанной необходимости; любое изменение — отдельный slice с повторным review.

- **C1A** (review `136`, accepted): env profile engine и immutable install transaction — `scripts/lib/prod-env-tool.py`, `scripts/tests/test-prod-env-install-transaction.sh` (37/37), `test-prod-env-profiles-mutations.sh` (14/14), `test-prod-env-root-identity.sh`; смежные: `test-prod-env-loader.sh`, `test-prod-env-profiles.sh` (75/75).
- **C1B1** (review `142`, accepted): installed-profile runtime `run-installed`/`run-clean`, canonical wrapper `scripts/prod-env-run.sh`, harnesses `test-prod-env-runtime.sh`, `test-prod-env-runtime-root.sh`, `test-prod-env-runtime-mutations.sh` (12 mutation cases).
- **Deploy source loader** (review `98`, accepted): `scripts/tests/test-prod-deploy-source-loader.sh` — **107 cases green** (ранее 111; канонический count — 107, фиксируется при приёмке).
- **Maintenance foundation**: `scripts/lib/prod-maintenance-state.sh`, `scripts/prod-maintenance-run.sh`, `scripts/tests/test-prod-maintenance-foundation.sh` — **20 cases green**.
- **Immutable manifest/runner/pinning**: `scripts/lib/prod-release-manifest.py`, `scripts/lib/prod-release.sh`, `scripts/prod-release-run.sh`, `scripts/tests/test-prod-release-pinning.sh` — **35 cases green**.
- **Immutable candidate builder**: `scripts/lib/prod-release-build.sh`, `scripts/tests/test-prod-release-build.sh` — **24 cases green**.
- C1B2 operational consumers (TZ `143`, correction TZ `145` после reject `144`): CLI-order исправлен по `145`; статус финального independent review см. в актуальной цепочке review-документов перед началом работ.

## 5. Текущий незавершённый slice: promotion / current / previous / rollback / GC

Три файла **НЕ приняты** (нет accepted review-документа):

- `scripts/lib/prod-release-promotion.sh` — 753 строки;
- `scripts/prod-release-promote.sh` — 112 строк;
- `scripts/tests/test-prod-release-promotion.sh` — 985 строк.

### 5.1 Фактическое состояние после read-only inspection (2026-07-17)

- Прежний harness разросся примерно до 900+ строк (текущие 985), был загрязнён диагностическими правками и ложнозелёными mutation checks. Ранее заявленный baseline «All 13 ... passed» **не является доказательством**.
- Фактический запуск harness сейчас: **красный уже на CASE01** — `rc=78`, `Error: release manifest validation failed`. Root cause: fixture-манифест в `create_sandbox_release` содержит 40-символьные значения `canon_versions_sha256`/`cache_identity_sha256` (строки 235-236 теста), а принятый валидатор `scripts/lib/prod-release-manifest.py` требует `^[0-9a-f]{64}$`. То есть текущий harness не согласован с принятой схемой манифеста.
- Ручная sandbox-репликация CASE01 с валидным 64-hex манифестом проходит (`rc=0`, `current -> releases/<sha>`): production-библиотека в happy path работоспособна, красный baseline — дефект harness-фикстур.
- Reasoning residue подтверждён: `test-prod-release-promotion.sh:826-829` (`# Wait, ...`, `# Let's check: ...`), а также `:147`, `:166` (`we should`) и `:358` (`wait:`).
- Mutation-блок harness: sed-замены мутанта без проверки точного count (1→0), мутант не прогоняется через `bash -n`, oracle встроен в тот же файл и не является внешним; соглашение «mutant вернул 0 = mutation verified» инвертирует смысл exit code.
- GC-тест исполняет production GC через **реальный git** репозитория (`git rev-parse --show-toplevel` из caller cwd, `git worktree list/remove`), а не sandbox mock registry; дефект production-кода — implicit repo discovery из caller cwd и отсутствие exact canonical repo binding (hardcoded fallback `/opt` в текущем коде нет).
- curl-mock вычисляет `release_sha` из `basename $(readlink -f current)` — то есть health «подтверждает» тот же symlink, который только что переключила библиотека; независимой identity-проверки нет.
- Дублирование boilerplate: `run_case_gc_inventory`, `run_case_gc_keep_two`, `run_case_gc_running_request` копируют `run_case` с drift (экранирование JSON в active.json у CASE10/13 отличается от CASE09).

### 5.2 Известные дефекты production-библиотеки и harness — обязательный checklist

1. При любой ошибке атомарно и доказуемо сохранять/восстанавливать ОБА `current` и `previous`: сейчас restore `previous` после failed switch (`prod-release-promotion.sh:373-377`) не проверяет rc восстановления; first-install rollback (`:412`) считает `rm -f current && rm -f previous` успешным rollback без restart/health старого стека.
2. Никаких swallowed restore через `|| true` или непроверенные rc на recovery-путях; каждый recovery-шаг проверяется, иначе `recovery_required`.
3. `maintenance.flag`: создавать `O_NOFOLLOW|O_EXCL`, проверять type/owner/group/mode, fsync file+dir (частично есть в `_prod_prm_create_flag`); удалять с доказательством/fsync только на safe success; при `recovery_required` флаг сохраняется (есть), но delete-path не проверяет mode (`_prod_prm_delete_flag` проверяет только uid/gid).
4. Symlink switch: root:astro fail-closed ownership, unique temp без unlink-race, postverify lstat/readlink/uid/gid, directory fsync (основа есть в `_prod_prm_python_switch`; cleanup temp в exception-path глотает ошибки unlink — `pass`).
5. Exact pointer target под `releases/<40hex>` без regex injection; текущая валидация `old_previous_val` (`:336`) и `prod_rel_rollback` (`:476`) смешивает `&&`/`||` без скобок — заменить на явную fail-closed логику.
6. Self-exec layout `scripts/lib -> scripts`: путь `../prod-maintenance-run.sh`/`../prod-release-promote.sh` проверять как resolved path внутри ожидаемого дерева, не только `[ -f ] && [ ! -L ]`.
7. Absolute `sudo`/`systemctl`/`curl` — есть; сохранить и покрыть подстановочными counts.
8. GC: hardcoded fallback `/opt` в текущем коде отсутствует; дефект — implicit repo discovery через `git rev-parse --show-toplevel` из caller cwd и отсутствие exact canonical repo binding: GC обязан работать только против явно заданного canonical repo и fail closed при его недоступности/невалидности; никаких raw unvalidated `rm -rf`; только exact validated registered worktree removal либо fail closed; `deleted_count` инкрементировать только после доказанного удаления (есть); GC при недоступном/невалидном registry обязан fail closed, а не «0 deleted, success».
9. Running-request metadata: fixed dir, no symlink, exact 40-hex SHA content, owner/group/mode validation (есть частично в `prod_rel_gc`); добавить fail-closed semantics при невалидном состоянии каталога.
10. frontend/api/sidecar health identity обязана реально подтверждать `release_sha`: mock обязан возвращать SHA из независимого per-service registry, а не из текущего symlink.
11. CASE06/07/08: exact assertions по current+previous+state(active.json)+flag+service-order для каждого из трёх failure-сценариев (сейчас service-order проверяется только у CASE06, previous/state/flag — не полностью).
12. GC-тест обязан использовать sandbox mock git registry (фейковый `git` с exact argv assertions), никогда реальный git.
13. Mutation self-proof: exact 1→0/replacement count на каждую sed-замену, `bash -n` мутанта, тот же oracle обязан стать nonzero; внешний (по отношению к мутанту) тест падает, если mutant passes.

### 5.3 Рекомендованный первый implementation step

Чисто переписать `scripts/tests/test-prod-release-promotion.sh` компактным честным harness:

- helper `replace_exact <file> <fixed-anchor> <replacement> <expected-count>` с pre/post counts и немедленным fail при несовпадении;
- единый `run_case` без дублирования GC-вариантов; fixture-манифесты валидны по принятой 64-hex схеме;
- sandbox mocks: `systemctl`, `curl` (per-service SHA registry), `git` (worktree registry), все в `$TEST_DIR/bin`;
- внешний mutation runner: mutant копируется, заменяется exact-one anchor, `bash -n`, oracle обязан nonzero;
- затем чинить production-библиотеку под красные тесты (см. 5.2), минимальными правками, без переписывания принятых зависимостей.

## 6. Остаток полного roadmap после promotion

Порядок ориентировочный по `69_AUDIT` (Recommended implementation order); каждый пункт — отдельный slice.

1. Backup/verify/offsite/restore/migration: provenance manifest, retention correction, restore drill, manual control plane; зачистка reasoning comments в старых harnesses.
2. TZ80 ephemeris production gate: central artifact/runtime manifest (`/opt/solarsage-ephemeris/releases/<id>` + `current`), запрет Moshier false-green (retflag обязан содержать `FLG_SWIEPH`), health/readiness identity, единый runtime owner вместо hardcoded `/opt/sweph/ephe`.
3. TZ81 Telegram bot launch gate: `getMe` exact bot id/username, BotFather profile/webapp menu, webhook policy, HMAC smoke, secret boundary.
4. Systemd units на immutable `current` release (root-owned runner/libexec), nginx maintenance flag/tmpfiles/sudoers, forced GitHub transport, workflows с manual approval и bounded Actions minutes.
5. frontend/API/sidecar health endpoints с exact release identity (SHA, calculation version, ephemeris identity).
6. Fresh-host bootstrap/readiness по `74_TZ`: non-cyclic order, key bootstrap, lockout-safe SSH hardening, runbook с actor/rc/evidence.
7. Полный offline/sandbox rehearsal: unit (`vitest`), backend (`pytest`), e2e (Playwright), structural suites; консолидированный docs/runbook.
8. Только после отдельного independent review всего пакета — ожидать ручную команду пользователя на реальный prod launch. Никаких «готов к запуску» заявлений без accepted review каждого gate.

## 7. Acceptance gates / Definition of done

Каждая проверка — из свежего shell, с честным rc, без `tail`-маскировки:

```bash
# статические
bash -n scripts/lib/prod-release-promotion.sh scripts/prod-release-promote.sh \
  scripts/tests/test-prod-release-promotion.sh
python3.12 -I -S -m py_compile scripts/lib/prod-release-manifest.py

# независимо принятые suites (counts фиксированы)
bash scripts/tests/test-prod-deploy-source-loader.sh      # 107 cases
bash scripts/tests/test-prod-maintenance-foundation.sh    # 20 cases
bash scripts/tests/test-prod-release-pinning.sh           # 35 cases
bash scripts/tests/test-prod-release-build.sh             # 24 cases

# promotion suite: зелёная независимо, mutation-proven
bash scripts/tests/test-prod-release-promotion.sh
bash scripts/tests/test-prod-release-promotion.sh         # второй прогон, детерминизм
```

- Promotion harness: зелёный при неизменённой production-библиотеке; каждый заявленный mutant даёт nonzero тем же oracle; внешний тест падает, если mutant passes.
- No reasoning/debug residue gate: `rg -n -i "wait|let'?s|ah!|ah,|we can|we should" scripts/lib/prod-release-promotion.sh scripts/prod-release-promote.sh scripts/tests/test-prod-release-promotion.sh` → пусто (ловит `wait`, `let's`/`lets`, `ah!`/`ah,`, `we can`, `we should`; проверено: на чистых lib/CLI возвращает пусто, на текущем harness находит строки 147, 166, 358, 826-829).
- No real-path mutation oracle: тест доказуемо не трогает `/opt/solarsage-runtime`, `/run`, `/var/lib`, реальные `systemctl`/`curl`/`git` (подстановочные post-counts = 0, mock-bin assertions).
- `git diff --check` чистый; dirty worktree сохранён (чужие изменения не тронуты).
- Ни одного production action: нет deploy/restart/reload/миграций/commit/push.
- Процесс по каждому дальнейшему slice: implementation → independent review → accepted/rejected документ в `docs/work/2026-07-15_production-server-bootstrap/`. Без accepted — следующий slice не начинать.

## 8. Immediate next task for Kimi K3

Строгий узкий порядок, без расширения scope:

- **A) Инвентаризация без изменений.** Зафиксировать фактическое состояние трёх promotion-файлов (раздел 5.1 этого документа как стартовая точка; перепроверить), список дефектов 5.2 и границы принятых зависимостей. Никаких правок кода на этом шаге.
- **B) Clean rewrite harness.** Переписать `scripts/tests/test-prod-release-promotion.sh` честным изолированным harness по 5.3: `replace_exact` helper с exact counts, валидные fixture-манифесты, sandbox mocks (`systemctl`/`curl` per-service registry/`git` registry), CASE06/07/08 exact current+previous+state+flag/service-order assertions, внешний mutation runner (1→0 count, `bash -n`, oracle nonzero). Harness сначала красный там, где библиотека дефектна (5.2).
- **C) Независимый red/green review.** Отдельный review-документ: какие кейсы красные по дефектам библиотеки, какие зелёные; подтверждение, что harness не ложнозелёный.
- **D) Production fixes.** Минимальными правками чинить `scripts/lib/prod-release-promotion.sh` (и при необходимости CLI) под красные тесты: restore-семантика обоих pointer'ов, flag lifecycle, GC fail-closed без fallback repo, exact target/owner проверки. Принятые файлы раздела 4 не трогать.
- **E) Повторный mutation/security review.** Полный прогон всех suites из раздела 7, residue-gate, no-real-path oracle, второй independent review с verdict accepted/rejected.
- **F) Только после accepted** — следующий roadmap slice из раздела 6 (первый: backup/offsite/restore/migration + зачистка reasoning comments в старых harnesses).

Остановиться после handoff каждого шага. Без commit/push, без production actions, без запуска следующего slice до accepted review текущего.
