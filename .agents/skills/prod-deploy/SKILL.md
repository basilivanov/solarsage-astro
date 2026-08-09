---
name: prod-deploy
description: Канонический выкат SolarSage Astro на production (astro.vasiliy-ivanov.ru) через deploy-production workflow — пошаговый runbook с preflight-проверками, watcher'ами, smoke и rollback. Использовать для любых «выкатывай в прод» задач.
---

# Production deploy — SolarSage Astro

Единственный канонический путь: GitHub Actions **`deploy-production.yml`** (manual `workflow_dispatch` из `main`). Всё остальное запрещено: ручной `docker compose up` на хосте, правки контейнеров руками, деплой «мимо гейтов». Orchestrator на хосте fail-closed — он сам делает бэкап, миграции, health-proof и один авто-rollback.

Этот скилл написан как runbook: выполнять шаги сверху вниз, не пропуская проверки. Если проверка не прошла — НЕ идти дальше, чинить причину по разделу «Диагностика» или эскалировать владельцу.

## STOP-условия (прерывать процедуру немедленно)

- CI на целевом SHA не зелёный → деплоить НЕЛЬЗЯ, гейт всё равно не пустит.
- Незакоммиченные/не запушенные изменения в main → сначала push.
- Кто-то пушит в main прямо сейчас → подождать: deploy берёт HEAD на момент диспатча, чужой коммит уедет в прод без проверки.
- Уже идёт другой deploy-run (`gh run list --workflow=deploy-production.yml --limit 1` → `in_progress`) → не диспатчить второй (concurrency group `production-deploy` всё равно поставит в очередь, но не плодить).

## Preflight — 6 проверок с эталонными ответами

Выполнять из `/opt/solarsage-astro`. Каждая проверка имеет критерий PASS. Любой FAIL → стоп.

**P1. Дерево чистое, HEAD == origin/main:**
```bash
git fetch origin main -q && git status -sb | head -3 && git rev-parse HEAD origin/main
```
PASS: `## main...origin/main` без `[ahead N]`; два SHA одинаковые. Untracked каталоги (`.codex/`, `artifacts/`, `.eval-runs/`) — ок. Modified файлы — FAIL (закоммитить или отложить).

**P2. CI зелёный на HEAD:**
```bash
gh run list --workflow=ci.yml --commit $(git rev-parse HEAD) --limit 1 --json status,conclusion --jq '.[0] | "\(.status) \(.conclusion)"'
```
PASS: `completed success`. `in_progress` → подождать. `completed failure` → чинить CI до зелёного, новый коммит, заново P1–P2.

**P3. Новые env-ключи есть на проде (если релиз добавляет/меняет env):**
```bash
# список новых ключей релиза: git diff <prev-prod-sha>..HEAD -- apps/api/app/core/config.py | grep '^+.*alias='
ssh -i ~/.ssh/solarsage_prod_server_ed25519 root@2.26.20.80 'grep -oE "^[A-Z_0-9]+=" /etc/solarsage/app.env | sort'
```
PASS: каждый новый alias из `config.py` присутствует в выводе. FAIL → добавить по процедуре «Изменения prod app.env» ДО диспатча. Значения ключей не печатать никуда.
Если релиз env не трогает — проверка пропускается.

**P3b. Версионные пины совпадают с кодом (если релиз трогает расчётный движок/эфемериды):**
```bash
# канон в репо:
grep "CALCULATION_VERSION = " packages/py-contracts/solarsage_contracts/versions.py
# пин на проде:
ssh -i ~/.ssh/solarsage_prod_server_ed25519 root@2.26.20.80 'grep -E "^(EXPECTED_CALCULATION_VERSION|EPHEMERIS_EXPECTED)" /etc/solarsage/app.env'
```
PASS: значения совпадают. FAIL → обновить пин в app.env до диспатча. Именно это убило deploy run 31339482621: sidecar репортил `ss-calc-1.3.0`, пин был `ss-calc-1.2.0` — health-proof fail-closed отработал правильно, но узнали об этом только на деплое.

**P4. Миграции БД (информационно, гейт их применит сам):**
```bash
git log --oneline $(git tag -l 'prod-*' | sort | tail -1)..HEAD -- apps/api/alembic/versions/ | head
```
PASS: любой вывод. Это FYI: orchestrator `migrate` применит их с бэкапом. Просто знать, что они есть.

**P5. UI/рендер менялся? → visual-бейзлайны свежие и runner-совместимые:**
```bash
git diff --name-only $(git tag -l 'prod-*' | sort | tail -1)..HEAD -- components/ app/ | head -5
```
Если вывод непустой:
```bash
node e2e/mock-visual/start-v2-preview.mjs > /tmp/v2p.log 2>&1 & echo $! > /tmp/v2p.pid
for i in $(seq 1 120); do curl -fsS -m 3 http://127.0.0.1:3003/day/2026-08-01 >/dev/null 2>&1 && break; sleep 1; done
E2E_BASE_URL=http://127.0.0.1:3003 CI=true pnpm exec playwright test e2e/mock-visual/ --project=chromium --project=mobile 2>&1 | tail -5
kill $(cat /tmp/v2p.pid)
```
PASS: `N passed` без `failed`. FAIL → раздел «Visual-gate» ниже. Если UI не менялся — пропустить.
Если менялся публичный DOM-контракт (testid/data-*/access-state) — дополнительно см. «Контракт-дрейф release e2e»: release-спеки в CI не гоняются, дрейф всплывёт только на деплое.

**P6. Прод жив и стартует не с колен:**
```bash
curl -fsS -m 10 https://astro.vasiliy-ivanov.ru/api/health | head -c 200
```
PASS: JSON с `git_sha`. FAIL → прод уже сломан ДО нас: не деплоить, эскалировать.

## Deploy — 3 шага

**D1. Диспатч:**
```bash
gh workflow run deploy-production.yml --ref main
sleep 15
RUN=$(gh run list --workflow=deploy-production.yml --limit 1 --json databaseId,headSha --jq '.[0] | "\(.databaseId) \(.headSha)"')
echo "RUN=$RUN"   # сверить: headSha == наш HEAD из P1
```
PASS: run создан и headSha совпадает с локальным HEAD. Не совпадает → кто-то запушил между P1 и D1; следить за ЭТИМ run'ом (он задеплоит чужой SHA) или отменить: `gh run cancel <id>`.

**D2. Watcher до конца (40–60 минут — норма, не дергать):**
```bash
while true; do
  R=$(gh run view ${RUN%% *} --json status,conclusion --jq '"\(.status) \(.conclusion)"')
  J=$(gh run view ${RUN%% *} --json jobs --jq '[.jobs[] | .name + ":" + (.conclusion // "running")] | join(" ")')
  echo "$(date +%H:%M:%S) $R | $J"; case "$R" in completed*) break;; esac; sleep 180
done
```
Гейты по порядку: `source-quality` → `visual-baselines` + `real-e2e` → `build` → `artifact-acceptance` → `deploy` → `tag`. Падение любого = fail-closed, последующие `skipped`. Диагностика — по разделу ниже.

**D3. Smoke (обязательно, в этом порядке):**
```bash
SHA=<задеплоенный sha>
curl -fsS https://astro.vasiliy-ivanov.ru/api/health    # git_sha == $SHA ?
ssh -i ~/.ssh/solarsage_prod_server_ed25519 root@2.26.20.80 '/usr/local/libexec/solarsage/prod-orchestrator status && docker ps --format "{{.Names}} {{.Status}}"'
git tag -l 'prod-*' | sort | tail -1                    # новый тег на наш SHA
```
PASS: health `git_sha` == HEAD; orchestrator `recorded active` == HEAD, api/sidecar/frontend `release_sha` совпадают, `migration marker status=heads_applied`; все контейнеры `Up (healthy)`; тег создан.
Затем прокликать фиче-поток релиза (для Today: открыть реальный день через веб/бот, проверить наличие narrative/сигналов).

## Диагностика упавшего run

```bash
gh run view ${RUN%% *} --json jobs --jq '.jobs[] | select(.conclusion=="failure") | .name'
gh run view ${RUN%% *} --log-failed | grep -E "Error|failed" | head -30
```

| Упавший job | Причина и действие |
|---|---|
| `source-quality` | CI на SHA не зелёный/нет run. Вернуться к P2. |
| `visual-baselines` | См. «Visual-gate» ниже. |
| `real-e2e` | Смотреть упавший spec в логе. Частая причина после UI-переделок: спеки ждут СТАРЫЙ DOM-контракт (см. «Контракт-дрейф release e2e» ниже). Отсутствие E2E_* секретов = fail-closed по дизайну — эскалировать владельцу, НЕ обходить. |
| `build` | Обычно инфра (registry/ephemeris bundle). Лог вверху job'а. Не ретраить вслепую — сначала причина. |
| `artifact-acceptance` | После 2026-08-10 job содержит только: clean-migration на эфемерной БД, sidecar-from-image + ephemeris identity, offline golden. Падение migration = миграции не применяются на чистой БД (реальная проблема релиза); sidecar/ephemeris = образ или bundle не тот; golden = детерминизм расчёта задет (не «флаки», эскалировать). Pre-convergence freeze/V2/UI шаги ОТКЛЮЧЕНЫ — не возвращать без реалигнмент-пакета (TODO(convergence-acceptance)). |
| `deploy` | `ssh ... prod-orchestrator status`; orchestrator уже сделал авто-rollback на предыдущий SHA. Разбор по его выводу в логе job'а. |

⚠️ Любая правка `.github/workflows/deploy-production.yml` должна сопровождаться прогоном `apps/api/tests/test_deploy_workflow_contracts.py` — CI содержит статические контракт-тесты на структуру workflow, они упадут на несогласованности (укушено 2026-08-10, run на ac941173).

## Контракт-дрейф release e2e (вторая ловушка)

Release-suite (`TODAY_CONVERGENCE_RELEASE_SPECS` в Makefile: onboarding-real, today-convergence, cross-feature-navigation, readings-horary, natal-report, referral-deeplink, payment-sandbox + 2 mock-visual) **не гоняется в CI на push** — только в deploy workflow. Поэтому ломающие DOM-контракт UI-изменения всплывают только на деплое, неделями позже коммита.

Правила:
- Меняешь публичный DOM-контракт (testid, data-*, access-state enum) — в том же релизе обновляй e2e-спеки и `e2e/fixtures.ts` (`waitForTodayState`), не только unit/mock-visual.
- Свежий юзер без доступа с convergence — это `data-access-state="preview"` (для past/today), НЕ `locked` (W-ACCESS.3). `locked` — только future-даты вне окна доступа.
- Тестиды старого Today (`day-summary-card`, `concrete-day-advice*`) мертвы; proof разблокированного дня — `data-access-state="full"` + `sphere-navigator` visible.
- Перед деплоем после UI-переделки имеет смысл прогнать release-suite локально заранее, а не узнавать о дрейфе из deploy-run'а.

Ретрай всего workflow (`gh run rerun`) допустим ТОЛЬКО при явной инфра-ошибке (сеть, registry timeout). При тестовых/визуальных падениях ретрай запрещён — чинить причину.

## Visual-gate: кросс-раннерная растеризация (главная ловушка)

GH-раннеры растеризуют шрифты недетерминированно между инстансами: один и тот же бейзлайн проходит в одном прогоне и падает в другом с ~1% пиксельного диффа на плотных текстовых страницах (доказано runs 31334707447/31335456568, 2026-08-09).

Правила:
- Глобальный порог — `maxDiffPixelRatio: 0.03` в `playwright.config.ts` (`expect.toHaveScreenshot`). НЕ возвращать `maxDiffPixels: 100` — абсолютный порог непереносим между машинами.
- В spec НЕ писать точные пиксельные высоты строк (на разных раннерах один элемент — 16px или 22px). Проверять: видимость, однострочность (sanity-bound), `scrollWidth ≤ clientWidth`, `scrollHeight ≤ clientHeight`, отсутствие горизонтального переполнения вьюпорта.
- Упавший на GH снапшот чинить так:
  ```bash
  gh run download ${RUN%% *} -n visual-regression-report -D /tmp/gh-report
  # найти test-results/**/<name>-actual.png, ПОСМОТРЕТЬ глазами — вёрстка intended, без разъезда
  # только потом скопировать поверх бейзлайна e2e/mock-visual/<spec>.spec.ts-snapshots/<name>-<project>-linux.png
  ```
  Коммитить actual РАННЕРА, а не локальный ререндер — бейзлайн должен быть из той же среды, что и гейт.
- `--update-snapshots` локально: убрать `CI=true` из env (Playwright запрещает update в CI).

## Изменения prod app.env

`/etc/solarsage/app.env` (root:astro 0640). Процедура без вариантов:

```bash
ssh -i ~/.ssh/solarsage_prod_server_ed25519 root@2.26.20.80
cp -a /etc/solarsage/app.env /etc/solarsage/app.env.bak-$(date +%Y%m%d)   # 1. бэкап ВСЕГДА
# 2. добавить/убрать ключи (heredoc >> для добавления; sed -i '/^KEY=/d' для удаления)
# 3. проверить ТОЛЬКО имена: grep -oE '^[A-Z_0-9]+=' /etc/solarsage/app.env | sort
```

- Править ДО диспатча deploy: контейнеры подхватывают env при recreate.
- Значения (секреты) никогда не печатать в stdout/логи/чат.
- Канон — dev `.env` (`/opt/solarsage-astro/.env`), но: `OPENROUTER_BASE_URL` на проде быть НЕ должно (прямой egress), legacy-флаги (`SOLARSAGE_V2_*`, `TODAY_VALENCE_*`) не носить.
- Перед добавлением ключа проверить, что код его читает: `rg 'alias="<KEY>"' apps/api/app/core/config.py`. Нет alias — ключ мусорный, не добавлять.

## Systemd/jobs на проде

- App — Compose-контейнеры; периодические джобы — systemd-таймеры, дёргающие `docker exec solarsage-api python -m app.jobs.<job>`. Эталон: `infra/systemd/solarsage-day-pregen-prod.{service,timer}` (04:07 MSK).
- Новый джоб: unit в репозиторий (`infra/systemd/`) → `install -m 644 -o root -g root` в `/etc/systemd/system/` → `systemctl daemon-reload && systemctl enable --now <name>.timer` → запись в AGENTS.md.
- Известный хвост: `solarsage-synastry-reconcile.timer` есть только на dev, на проде его нет (не «поломка», просто не завезли).

## Rollback

App-rollback (без отката схемы БД):
```bash
ssh -i ~/.ssh/solarsage_prod_server_ed25519 root@2.26.20.80 \
  '/usr/local/libexec/solarsage/prod-orchestrator rollback <previous-sha> --manual-confirm'
```
`<previous-sha>` — из `prod-orchestrator status`, поле `recorded previous`. Схему БД rollback НЕ трогает; откат схемы — только ручное восстановление из pre-migration дампа (эскалация владельцу, самому не делать).

## Журнал состояния (2026-08-10)

- До сессии 2026-08-09/10 прод жил на `97db469e7a9b` (2026-07-27).
- Сделано в сессии: починен main CI (mypy-аннотация `_presentation`, branch coverage 75.7→76.3% через `today-formatters.test.ts`); visual-gate приведён к runner-proof виду (3% ratio, GH-rendered бейзлайны hero-tense/today-navigator, env-agnostic геометрия в long-impulse spec); prod app.env дополнен narrative/pregen ключами (бэкап `app.env.bak-20260809`); поставлен prod day-pregen timer (04:07 MSK); release e2e-спеки выровнены под convergence-контракт (`waitForTodayState` locked|preview, referral proof через data-access-state=full + sphere-navigator).
- **artifact-acceptance реализован заново частично**: pre-convergence шаги (seed, audit freeze ×2, V2 API proof, same-payload UI proof) отключены в `deploy-production.yml` — они валидировали retired today.v2.2-контракт и никогда не работали после W6-S2 (нет live API в job). Остались: clean-migration, sidecar-from-image + ephemeris identity, offline golden. Реалигnment под convergence (новый freeze + UI proof) — отдельный пакет, см. TODO(convergence-acceptance) в workflow.
