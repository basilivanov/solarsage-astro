# Review R10B-R1 — workflow secret boundary, tool order, smoke accuracy

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: точечные corrections; commit/push/live deploy запрещены.

## Обязательные исправления

### 1. Setup order and cache

В `.github/workflows/e2e.yml` `pnpm/action-setup@v4` должен идти до `actions/setup-node@v4` с `cache: pnpm`, как уже сделано в `ci.yml`/visual. У `setup-node` не должно быть cache lookup до наличия pnpm.

Добавь `cache-dependency-path` для Python setup (`apps/api/pyproject.toml`, `apps/solarsage/pyproject.toml`, `packages/py-contracts/pyproject.toml`) если cache=pip используется.

Установку Playwright browsers выполняй до запуска долгоживущих сервисов либо гарантируй, что её failure вызывает cleanup trap; не оставляй процессы при apt/browser failure.

### 2. Secret boundary around frontend build

Секреты `E2E_TELEGRAM_BOT_TOKEN` и `E2E_OPENROUTER_API_KEY` нужны API и test process, но не Next build. Не экспортируй их в parent shell перед `pnpm run build`; используй scoped `env` для API process и для Playwright/generator. Перед frontend build явно убери secret vars из child environment (`env -u ...`) либо эквивалентно.

Не выводи env values и не добавляй их в artifacts.

### 3. Correct API test settings

- Используй `LLM_MODEL=...`, а не неиспользуемый `OPENROUTER_MODEL`, если нужно зафиксировать test model.
- Добавь synthetic `JWT_SECRET` достаточной длины, если runtime config требует его.
- Сохрани `DATABASE_URL`/`SOLARSAGE_URL` canonical ports 5432(service DB internal), 8000(API), 18091(sidecar), 3002(frontend).

### 4. Smoke suite and runbook must match

Сейчас runbook обещает Today + Calendar + navigation/auth, а workflow запускает `today.spec.ts onboarding-real.spec.ts`. Выбери один фактический набор и синхронно поправь оба места. Рекомендуемый smoke (без внешнего Geonames/onboarding зависимости):

```bash
pnpm exec playwright test today.spec.ts calendar.spec.ts cross-feature-navigation.spec.ts --project=chromium
```

Full suite запускай явной командой без дублирования `--project` через package script (например, `pnpm exec playwright test --project=chromium`).

### 5. Shell robustness

- PID arguments quote safely: `kill "$(cat pidfile)"`;
- readiness curls use bounded `--connect-timeout`/`--max-time`;
- cleanup trap survives failures in browser install, build, and tests;
- add `required: false`/explicit default for workflow input if needed by GitHub schema.

## Проверки

```bash
python3 - <<'PY'
import yaml
for p in [".github/workflows/e2e.yml", ".github/workflows/visual-regression.yml"]:
    yaml.safe_load(open(p))
print("yaml_ok")
PY
rg -n "OPENROUTER_MODEL|onboarding-real\.spec|setup-node@v4" .github/workflows/e2e.yml docs/PRODUCTION_RUNBOOK.md && true
! rg -n "python-version: '3\.11'|requirements\.txt|8001|updateSnapshots:.*missing" .github/workflows/e2e.yml .github/workflows/visual-regression.yml playwright.config.ts
git diff --check
```

Не читать/копировать настоящий `.env.production`; synthetic redacted tests only. Не commit/push/live actions.
