# S2.W6 ТЗ — merge в main и безопасный production deploy

> Amendment: если Stage A добавила `packages/py-contracts`, release обязан
> построить один wheel из принятого main SHA, записать его SHA-256 и установить
> один и тот же wheel в `apps/solarsage/venv` и `apps/api/.venv` до restart.
> Изменение любого файла `packages/py-contracts/**` считается dependency/runtime
> change даже при неизменном app `pyproject.toml`. Полный порядок и proof заданы
> в `40_STAGE_A_SHARED_PYTHON_CONTRACT_PLATFORM_TZ.md` и
> `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md`.

Master:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/00_MASTER_TZ.md
```

Prerequisite: архитектор письменно принял `READY_STAGE_2_FOR_MAIN_RELEASE` и
отдельно дал команду выполнять S2.W6. До этой команды этот файл только план,
никаких изменений `main`, systemd или production runtime не делать.

## 1. Цель и неизменяемые ограничения

Выпустить принятый end-to-end Today V2 pipeline:

```text
sidecar timing
  -> API horizons/actions/provenance
  -> generated OpenAPI TypeScript + Zod contract
  -> frontend human-first presentation
```

Итогом должны быть одновременно:

- clean `main` с merge commit программы;
- `origin/main` указывает на тот же SHA;
- production sidecar/API/frontend запущены из этого checkout;
- production Next build лежит в каноническом `.next-prod`;
- V2 feature flags включены в каноническом backend env;
- реальный Telegram HMAC E2E проходит без fixture/route interception;
- rollback build, git SHA и команды сохранены;
- ни один секрет или персональные данные не попали в callback/artifacts/logs.

Не использовать:

- ручной `uvicorn`;
- API на `8001`;
- runtime fixture/mock;
- `git reset --hard`, `git checkout -- <path>` или удаление чужих файлов;
- `scripts/deploy.sh` без отдельного review: в текущей версии он ошибочно
  проверяет API health вместо sidecar health;
- destructive cleanup старого production build до полного smoke;
- force-push.

## 2. Канонические runtime targets

```text
PostgreSQL             127.0.0.1:5433  solarsage-db
SolarSage sidecar      127.0.0.1:18091 solarsage-sidecar.service
FastAPI                127.0.0.1:8000  solarsage-api.service
Next production        127.0.0.1:3002  solarsage-frontend.service
Nginx                  80/443          nginx.service
Production dist        /opt/solarsage-astro/.next-prod
Backend env            /opt/solarsage-astro/.env
Public canonical host  https://dev.astro.vasiliy-ivanov.ru
```

Не изменять nginx, systemd unit files или портовую схему, если preflight не
докажет отдельную реальную необходимость. Эта feature не требует таких
изменений.

## 3. Release identifiers и каталоги

В начале вычислить, но не подставлять вручную:

```bash
REPO=/opt/solarsage-astro
FEATURE_BRANCH=preview/solarsage-v2-human-first-navigator-ux
FEATURE_SHA=$(git rev-parse "$FEATURE_BRANCH")
PREVIOUS_MAIN_SHA=$(git rev-parse main)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RC_DIST=".next-release-${STAMP}"
ROLLBACK_DIST=".next-prod.rollback-${PREVIOUS_MAIN_SHA:0:12}-${STAMP}"
```

В callback указать эти значения, кроме содержимого env.

## 4. Preflight до изменения main

### 4.1 Git proof

Проверить:

```bash
git fetch origin --prune
git status --short --branch
git rev-parse "$FEATURE_BRANCH"
git rev-parse "origin/$FEATURE_BRANCH"
git rev-parse main
git rev-parse origin/main
git merge-base --is-ancestor origin/main "$FEATURE_BRANCH"
git log --oneline --decorate origin/main.."$FEATURE_BRANCH"
git diff --check origin/main..."$FEATURE_BRANCH"
```

Требования:

- feature branch clean;
- local feature SHA equals remote feature SHA;
- local main equals origin/main;
- origin/main является предком feature branch;
- в diff нет forbidden/unrelated paths;
- все принятые wave commits присутствуют;
- нет незакоммиченных generated contract artifacts.

Если `origin/main` ушёл вперёд, остановиться с `BLOCKED_S2_W6_MAIN_MOVED` и
точными SHA. Не выполнять автоматический rebase/merge без architect review.

### 4.2 Full release gates ещё на feature branch

Повторить, даже если S2.W5 уже запускал их:

```bash
pnpm install --frozen-lockfile
pnpm contracts:generate
pnpm contracts:check
npx vitest run
(
  cd apps/solarsage
  python -m pytest tests/ -q
)
(
  cd apps/api
  source .venv/bin/activate
  python -m pytest tests/ -q
)
pnpm guardrails:prod
pnpm guardrails:contracts
git diff HEAD --check
```

`pnpm contracts:generate` не должен оставлять diff. Если оставляет — release
останавливается; generated artifacts должны быть исправлены и приняты отдельной
волной, не коммититься молча в S2.W6.

### 4.3 Runtime/environment read-only audit

Проверить без печати значений secrets:

```bash
systemctl is-active solarsage-sidecar.service
systemctl is-active solarsage-api.service
systemctl is-active solarsage-frontend.service
systemctl is-active nginx.service
curl --fail --silent http://127.0.0.1:18091/v1/health
curl --fail --silent http://127.0.0.1:8000/api/health
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' \
  http://127.0.0.1/
sudo nginx -t
```

Для env вывести только наличие и boolean state allowlisted flags, никогда не
весь файл:

```text
SOLARSAGE_V2_ENABLED
SOLARSAGE_V2_FRONTEND_ENABLED
```

Нельзя выводить raw Telegram initData, bot token, database URL, cookies,
LLM/API keys или полное `.env`.

## 5. Merge в main

Только после полного preflight:

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff "$FEATURE_BRANCH" \
  -m "feat(today): ship real personal horizons v2"
```

После merge, до push:

```bash
git status --short --branch
git diff --check HEAD^..HEAD
git log -1 --oneline --decorate
pnpm contracts:check
npx tsc --noEmit
```

Требуется clean worktree. Затем:

```bash
git push origin main
```

Доказать:

```bash
MAIN_SHA=$(git rev-parse main)
ORIGIN_MAIN_SHA=$(git rev-parse origin/main)
test "$MAIN_SHA" = "$ORIGIN_MAIN_SHA"
```

Если push rejected из-за изменившегося remote main — не force-push. Остановить
release с `BLOCKED_S2_W6_PUSH_RACE`.

## 6. Python dependencies

Сравнить dependency files между `PREVIOUS_MAIN_SHA` и `MAIN_SHA`.

Если sidecar dependency manifests не менялись — не выполнять install.
Если менялись, использовать только sidecar venv:

```text
/opt/solarsage-astro/apps/solarsage/venv
```

Если API dependency manifests не менялись — не выполнять install.
Если менялись, использовать только API venv:

```text
/opt/solarsage-astro/apps/api/.venv
```

Команду установки выбрать по уже существующему canonical manifest/lockfile,
не создавать новый способ управления зависимостями в release wave. После
install выполнить `pip check` соответствующим venv. Не использовать global
Python и не менять второй проект `/opt/astro-project`.

## 7. Feature flags и env

Новый code path должен быть уже полностью проверен до включения flags.

Если оба flags уже true — ничего не менять.

Если хотя бы один false/missing:

1. создать root-readable backup рядом с env:

```text
/opt/solarsage-astro/.env.rollback-<STAMP>
```

2. сохранить ownership/mode исходного `.env`;
3. изменить только две строки:

```text
SOLARSAGE_V2_ENABLED=true
SOLARSAGE_V2_FRONTEND_ENABLED=true
```

4. не дублировать ключи;
5. валидировать только boolean states через application settings import;
6. не печатать другие env values.

Если безопасное scoped редактирование невозможно или файл содержит дубли,
остановиться с `BLOCKED_S2_W6_ENV` и показать только имена конфликтующих keys,
без значений.

## 8. Build release candidate без остановки production

До restart production собрать отдельный candidate dist:

```bash
NEXT_DIST_DIR="$RC_DIST" pnpm build
```

Требования:

- build успешен;
- candidate не равен `.next-prod`;
- generated `next-env.d.ts`/`tsconfig.json` noise отсутствует или восстановлен
  byte-for-byte без destructive git commands;
- `git status` остаётся clean;
- candidate принадлежит user/group `astro`;
- старый `.next-prod` продолжает обслуживать порт 3002.

### Candidate smoke на временном порту

Запустить candidate как user `astro` на свободном loopback порту `3010`, с:

```text
NODE_ENV=production
PORT=3010
NEXT_DIST_DIR=<RC_DIST>
```

Это временный foreground/managed shell process только для Next candidate smoke,
не новый uvicorn и не новый постоянный сервис.

Проверить:

```bash
curl --fail http://127.0.0.1:3010/
```

и focused frontend Playwright smoke против `3010`. После проверки корректно
остановить только candidate process и доказать, что порт 3010 свободен.

Если candidate smoke падает, не трогать systemd и `.next-prod`.

## 9. Atomic build swap и restart order

### 9.1 Сохранить rollback build

Перед swap проверить наличие `.next-prod`. Затем:

1. остановить только frontend service;
2. переименовать текущий `.next-prod` в вычисленный `ROLLBACK_DIST`;
3. переименовать `RC_DIST` в `.next-prod`;
4. сохранить ownership `astro:astro`;
5. не удалять `ROLLBACK_DIST` до полного post-deploy acceptance.

Операции rename должны происходить на том же filesystem. Если шаг swap
прерывается, немедленно вернуть предыдущий `.next-prod` до restart.

### 9.2 Restart dependency order

После build swap:

```text
1. sudo systemctl restart solarsage-sidecar.service
2. дождаться active + GET http://127.0.0.1:18091/v1/health
3. sudo systemctl restart solarsage-api.service
4. дождаться active + GET http://127.0.0.1:8000/api/health
5. sudo systemctl start solarsage-frontend.service
6. дождаться active + GET http://127.0.0.1:3002/
7. sudo systemctl reload nginx.service только если nginx -t PASS;
   при отсутствии nginx config changes reload не обязателен
```

Для каждого wait использовать bounded retry с общим timeout не более 120
секунд и коротким interval. Не делать бесконечных waits.

После каждого restart проверить последние логи, редактируя потенциально
чувствительные строки в callback:

```bash
journalctl -u <unit> --since '<release start UTC>' --no-pager
```

В callback — только summary/count/error class, не raw request data.

## 10. Post-deploy smoke

### 10.1 Services и routes

Доказать:

```bash
systemctl is-active solarsage-sidecar.service
systemctl is-active solarsage-api.service
systemctl is-active solarsage-frontend.service
systemctl is-active nginx.service
curl --fail http://127.0.0.1:18091/v1/health
curl --fail http://127.0.0.1:8000/api/health
curl --fail http://127.0.0.1:3002/
curl --fail http://127.0.0.1/api/health
curl --fail https://dev.astro.vasiliy-ivanov.ru/api/health
curl --fail https://dev.astro.vasiliy-ivanov.ru/
```

Проверить, что каждый canonical port слушает ровно ожидаемый process/service.

### 10.2 Real authenticated payload

Использовать существующий:

```text
scripts/generate-telegram-test-initdata.py
```

и существующий real-E2E auth flow. Не печатать сгенерированный initData.

Получить реальный `/api/day/<date>` и сохранить redacted audit artifact в:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/release/
  production-payload-proof.redacted.json
```

Artifact содержит только:

- meta/version fields;
- capabilities;
- horizon intro structure/text;
- horizon IDs/order;
- timing fields/phases;
- sphere keys;
- action text and provenance IDs;
- activation evidence IDs/types/timing required for referential proof.

Удалить/не сохранять:

- auth headers/cookies/initData;
- имя/Telegram ID;
- birth date/time/location and coordinates;
- request headers;
- unrelated profile data.

Assertions:

- payload is `today.v2.1` / frontend version `3` / content version `10`;
- capabilities include horizon timing/guidance/personal actions;
- exactly `long`, `medium`, `fast` in this order;
- required timing values non-null for selected horizons;
- all evidence references resolve;
- no forbidden technical jargon in human fields;
- no fixture marker/source;
- cache identity uses new version family.

### 10.3 Real browser E2E

Run the accepted production real E2E spec against:

```text
https://dev.astro.vasiliy-ivanov.ru
```

Rules:

- real Telegram HMAC;
- no `page.route('/api/**')`;
- no `fixture=` query;
- no `/api/dev-fixtures/` requests;
- response source `backend-horizons`;
- all three horizons and personal actions visible;
- 12 navigator statuses visible;
- no browser console/page errors;
- save final mobile screenshot and sanitized network request-name/status trace.

Expected release artifacts:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/release/
  production-real-day-mobile.png
  production-network-proof.redacted.json
  production-payload-proof.redacted.json
  release-report.md
```

Artifact commit policy: if these paths are intended repository evidence and do
not contain secrets/PII, make a dedicated post-deploy evidence commit on main
and push it. If any artifact cannot be safely redacted, do not commit it; record
only the PASS summary in `release-report.md`.

## 11. Rollback triggers

Rollback immediately if any condition holds:

- sidecar/API/frontend service cannot become healthy within timeout;
- real auth fails because of this release;
- day endpoint returns 5xx or invalid generated wire shape;
- selected horizons have dangling provenance;
- frontend cannot render a real day;
- sustained new error loop appears in journals;
- production uses fixture/legacy-derived source for fresh V2 payload;
- new latency materially breaches accepted S2.W1/S2.W5 budget.

## 12. Rollback procedure

Rollback must restore code, build and env consistently.

1. Stop frontend.
2. Preserve failed `.next-prod` as `.next-prod.failed-<MAIN_SHA>-<STAMP>`.
3. Rename `ROLLBACK_DIST` back to `.next-prod`.
4. Restore scoped env backup if flags were changed.
5. Create a normal `git revert -m 1 <merge-sha>` commit on main; never reset
   published main and never force-push.
6. Push the revert commit.
7. Restart sidecar, API, frontend in the same dependency order.
8. Repeat health + prior-version authenticated smoke.

If immediate service restoration is urgent, build/env/code restoration can
precede creation of the revert commit, but the published branch must be made
consistent in the same rollback operation and reported explicitly.

## 13. Final release callback

```text
READY_S2_W6_PRODUCTION
feature_sha: <sha>
previous_main_sha: <sha>
merge_sha: <sha>
origin_main_sha: <sha; equals merge/evidence SHA>
evidence_commit_sha: <sha or NONE>
git_clean: YES
contracts: PASS
vitest: <count/pass>
sidecar_pytest: <count/pass>
api_pytest: <count/pass>
guardrails: PASS
candidate_build: PASS <dist>
rollback_build: <dist>
flags: SOLARSAGE_V2_ENABLED=true; SOLARSAGE_V2_FRONTEND_ENABLED=true
services: sidecar=active; api=active; frontend=active; nginx=active
ports: 18091=sidecar; 8000=api; 3002=frontend
health: sidecar=PASS; api=PASS; frontend=PASS; nginx=PASS
payload_versions: <values>
horizons: long,medium,fast
frontend_data_source: backend-horizons
provenance_integrity: PASS
real_telegram_e2e: PASS
fixture_requests: 0
console_errors: 0
artifacts: <safe paths>
rollback_command: git revert -m 1 <merge_sha>
secrets_or_pii_in_report: NO
```

После этого кодер останавливается. Итоговую архитектурную приёмку, отметку goal
complete и сообщение пользователю делает архитектор.
