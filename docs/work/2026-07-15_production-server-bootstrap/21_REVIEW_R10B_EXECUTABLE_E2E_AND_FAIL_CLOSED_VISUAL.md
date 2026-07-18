# R10B — executable manual real E2E and fail-closed visual baselines

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: исправить до принятия workflows; commit/push/live production deploy запрещены.

## Найденные блокеры

1. `.github/workflows/e2e.yml` запускает только API на 8001, но Playwright ожидает frontend на 3002; sidecar 18091 не запускается.
2. Real-auth fixtures вызывают `scripts/generate-telegram-test-initdata.py`, который читает `.env.production`; такого файла в GitHub checkout нет.
3. Visual workflow делает лишний `pnpm build`, хотя `pnpm preview:v2` запускает Next dev, и lifecycle preview разнесён по steps.
4. `playwright.config.ts` использует `updateSnapshots: "missing"` по умолчанию, поэтому CI может создать отсутствующий baseline вместо fail-closed ошибки.

## Scope

Измени:

```text
.github/workflows/e2e.yml
.github/workflows/visual-regression.yml
scripts/generate-telegram-test-initdata.py
apps/api/tests/test_telegram_hmac.py
playwright.config.ts
docs/PRODUCTION_RUNBOOK.md
```

Не менять production deploy workflow, runtime auth/API behavior, product frontend или secrets.

## 1. HMAC generator — env-first, file fallback

В `load_bot_token()`:

- сначала читать `TELEGRAM_BOT_TOKEN` из process environment;
- trim, non-empty -> использовать;
- если env отсутствует/empty, сохранить локальный fallback на `.env.production`;
- не печатать token ни в success, ни в error;
- обновить module contract/docstring.

Добавить тесты:

- env token работает без `.env.production`;
- empty env корректно falls back на synthetic temp env file/monkeypatch path;
- output никогда не содержит token;
- существующий synthetic user safety test сохранить.

Не читать настоящий `.env.production` в harness.

## 2. Manual real E2E workflow — полный локальный stack

Триггер остаётся только `workflow_dispatch`. Добавь input:

```yaml
suite:
  type: choice
  options: [smoke, full]
  default: smoke
```

Секреты (repository/environment secrets, значения никогда не печатать):

```text
E2E_TELEGRAM_BOT_TOKEN
E2E_OPENROUTER_API_KEY
```

Перед install/start fail-fast проверить только наличие через `-n`, без echo values.

Установить:

- `packages/py-contracts`;
- `apps/solarsage[dev]`;
- `apps/api[dev]`;
- Node/pnpm dependencies;
- Playwright Chromium.

Поднять в одном lifecycle step или в steps с гарантированным cross-step cleanup:

1. Sidecar `127.0.0.1:18091` с `SOLARSAGE_EPHEMERIS_PATH=/tmp/solarsage-e2e-ephe` (создать directory; Moshier probe допустим) и bounded `/v1/health` check.
2. API `127.0.0.1:8000` — canonical port, не 8001 — с Postgres service DB и env:
   - `APP_ENV=test`;
   - `APP_DOMAIN=localhost`;
   - `DEV_MODE=false`;
   - `DATABASE_URL=postgresql+asyncpg://astro:astro_test_password@127.0.0.1:5432/astro`;
   - `TELEGRAM_BOT_TOKEN=${{ secrets.E2E_TELEGRAM_BOT_TOKEN }}`;
   - `SESSION_COOKIE_SECURE=false`;
   - `GRACE_USER_SALT` synthetic;
   - `SOLARSAGE_URL=http://127.0.0.1:18091`;
   - `LLM_PROVIDER=openrouter`;
   - `OPENROUTER_API_KEY=${{ secrets.E2E_OPENROUTER_API_KEY }}`;
   - low-cost explicitly pinned test model already supported by current provider contract;
   - required CORS/local values as needed.
3. Frontend на canonical `127.0.0.1:3002`: production build/start либо dev server, но `/api/*` должен реально идти на API 8000. Если production build — выполнить `pnpm build`, затем `pnpm exec next start -H 127.0.0.1 -p 3002`; если dev — документировать причину. Bounded curl readiness.

Все процессы писать в отдельные `/tmp/solarsage-e2e-*.log`, PIDs очищать через trap. При failure выводить только последние 100 redacted-safe log lines; API structured redactor должен исключать secrets, но shell всё равно не делать `set -x`.

Playwright env:

```text
E2E_BASE_URL=http://127.0.0.1:3002
E2E_API_BASE_URL=http://127.0.0.1:8000
TELEGRAM_BOT_TOKEN=<E2E secret>
CI=true
```

Smoke suite по умолчанию должен быть ограничен реальными наиболее ценными spec-файлами (Today + Calendar + one navigation/auth path) и Chromium, чтобы беречь минуты/LLM cost. `full` может запускать весь real suite, но явно вручную. Не включать `e2e/mock-visual` в real suite.

Artifacts: `playwright-report/`, `test-results/`, server logs на failure; retention 7–14 days. Не загружать env/secret files.

## 3. Visual workflow

- Удалить лишний `pnpm run build`.
- Объединить start `pnpm preview:v2`, readiness и Playwright command в один shell step с одним trap, чтобы PID cleanup был гарантирован и не зависел от cross-step background process semantics.
- Bounded readiness на 3003 сохранить.
- На failure вывести last 100 preview log lines.
- Запускать `e2e/mock-visual` Chromium + mobile как сейчас.
- Upload both `playwright-report/` and `test-results/`; diff path должен включать `test-results/**/*-diff.png`, а не только `e2e/**/*-diff.png`.

## 4. Fail-closed baseline policy

В `playwright.config.ts`:

```ts
updateSnapshots: process.env.UPDATE_SNAPSHOTS === "true" ? "all" : "none"
```

или эквивалент, при котором обычный CI/local run не создаёт missing snapshots. Обновление baseline — только explicit `UPDATE_SNAPSHOTS=true`/CLI review action.

Добавить/обновить комментарий и test, если рядом есть config tests. Не менять tolerance в этой задаче.

## 5. Runbook

Кратко документировать:

- visual и real E2E manual-only;
- required GitHub secrets `E2E_TELEGRAM_BOT_TOKEN`, `E2E_OPENROUTER_API_KEY`;
- dedicated test bot/provider key recommended, с spending limit;
- production token не использовать для routine CI;
- smoke default / full explicit;
- snapshots fail closed and update only deliberately.

## Проверки

```bash
python3 -m pytest apps/api/tests/test_telegram_hmac.py -q
npx tsc --noEmit
python3 - <<'PY'
import yaml
for p in [".github/workflows/e2e.yml", ".github/workflows/visual-regression.yml"]:
    yaml.safe_load(open(p))
print("yaml_ok")
PY
rg -n "8001|requirements\.txt|python-version: '3\.11'|updateSnapshots:.*missing|e2e/visual-regression\.spec" .github/workflows/e2e.yml .github/workflows/visual-regression.yml playwright.config.ts && exit 1 || true
git diff --check
```

Локальный visual smoke разрешён на 3003 без production API и без snapshot update. Real E2E с внешним provider не запускать без dedicated test secrets. Не читать настоящий `.env.production`; synthetic fixtures only.
