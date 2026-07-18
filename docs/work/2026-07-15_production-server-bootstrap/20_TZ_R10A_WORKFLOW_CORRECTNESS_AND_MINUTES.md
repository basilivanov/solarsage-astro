# R10A — CI/E2E/visual workflow correctness and GitHub minutes budget

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: implement + review; commit/push/live production deploy запрещены.

## Цель

Сделать GitHub Actions самодостаточными и реально исполняемыми после перевода репозитория в private, не меняя ручной характер production deploy. Workflows должны использовать существующие тесты/fixtures, не ссылки на удалённые файлы, иметь явные permissions/timeouts и не сжигать минуты на каждый push без необходимости.

## Scope

Измени только:

```text
.github/workflows/ci.yml
.github/workflows/e2e.yml
.github/workflows/visual-regression.yml
```

Сохрани `deploy-production.yml` без функциональных изменений R8/R9A.

## 1. Общие правила

- Для workflows, которые делают `actions/checkout`, выставить `permissions: { contents: read }` (private repo должен клонироваться; не выдавать write/issue права).
- Для deploy workflow уже действует `permissions: {}` — не менять.
- Для каждого job добавить bounded `timeout-minutes`; не оставлять бесконечный default.
- Не добавлять `push` trigger в E2E/visual. CI оставь на `pull_request` в `main` + `workflow_dispatch`; визуал и E2E — `workflow_dispatch` only, чтобы не расходовать 2000 минут автоматически.
- Все action versions — текущие major, как в репозитории (`checkout@v4`, `setup-node@v4`, `setup-python@v5`, `pnpm/action-setup@v4`, `upload-artifact@v4`).
- Не выводить secrets; в workflow shell использовать env-контекст, но никаких `${{ secrets.X }}` внутри command string.

## 2. `ci.yml`

- Добавить workflow-level `permissions: contents: read`.
- Сохранить четыре существующих job и их реальные команды.
- Добавить timeout: backend 20m, sidecar 15m, frontend 20m, contracts 20m (или более строгие bounded значения, если все команды успевают).
- Node jobs используют pnpm `10.32.1` и Node `22` (или согласованный production-compatible `20.9+`; не использовать Python 3.11 для backend).
- Python jobs используют `actions/setup-python@v5` с `3.12`, ставят `packages/py-contracts` и соответствующий пакет через pyproject extras, не `requirements.txt`.
- Не добавлять реальные Telegram/API secrets.

## 3. `e2e.yml`

Сейчас workflow ссылается на отсутствующий `apps/api/requirements.txt` и Python 3.11. Исправить:

- workflow-level `permissions: contents: read`;
- `workflow_dispatch` only сохранить;
- timeout job не более 25m;
- Node 22 + pnpm 10.32.1;
- Python 3.12;
- установить backend так:

```bash
python -m pip install --upgrade pip
python -m pip install -e ./packages/py-contracts
python -m pip install -e './apps/api[dev]'
python -m pip check
```

- миграции запускать из `apps/api` через `.venv` не требуется в CI, но `alembic upgrade head` должен видеть установленный пакет и test `DATABASE_URL`;
- сохранить Postgres/Redis service containers и безопасные test-only values;
- запуск FastAPI должен использовать Python 3.12 и реально установленный `uvicorn`;
- сохранить Playwright Chromium install, но не устанавливать WebKit без тестов, если это не требуется;
- `E2E_BASE_URL` и API URL должны совпадать с поднятым backend;
- удалить или отключить `github-script` PR comment: при `permissions: contents: read` он не имеет issue write; workflow manual-only, поэтому комментарий не является acceptance requirement;
- artifact upload оставь с bounded retention (7–14 дней).

## 4. `visual-regression.yml`

Текущий путь `e2e/visual-regression.spec.ts` отсутствует. Используй существующий test harness:

- workflow-level `permissions: contents: read`;
- `workflow_dispatch` only;
- timeout job 25m;
- Node 22 + pnpm 10.32.1;
- `pnpm install --frozen-lockfile`;
- `pnpm exec playwright install --with-deps chromium`;
- запускать test-only preview через существующий `pnpm preview:v2` (порт 3003; mock API 18092) в фоне, писать lifecycle в `/tmp/solarsage-v2-preview.log`, сохранить PID и корректно завершить его в `trap`;
- bounded readiness loop с `curl --connect-timeout 2 --max-time 5` на `http://127.0.0.1:3003/day/2026-07-08` (не `wait-on`);
- запускать существующие specs:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  CI=true pnpm exec playwright test e2e/mock-visual --project=chromium --project=mobile
```

- не использовать production API/port 8000;
- при failure вывести последние 100 строк preview log, не secrets;
- upload `playwright-report`, `test-results`, diff/snapshot artifacts с retention 7–14 дней и `if: always()`/`if: failure()` по смыслу;
- не обновлять snapshots автоматически.

## 5. Проверки

До handoff выполнить без commit/push/deploy:

```bash
python3 - <<'PY'
from pathlib import Path
for p in map(Path, [".github/workflows/ci.yml", ".github/workflows/e2e.yml", ".github/workflows/visual-regression.yml"]):
    text = p.read_text()
    assert "timeout-minutes:" in text, p
    assert "permissions:" in text, p
print("workflow_static_contract_ok")
PY

rg -n "e2e/visual-regression\.spec\.ts|apps/api/requirements\.txt|python-version: '3\.11'|npx wait-on" .github/workflows && exit 1 || true
git diff --check
```

Также проверь YAML parse доступным локальным инструментом (если установлен) и не меняй frozen paths (`.grace/`, `artifacts/design/`, `docs/superpowers/plans/...`, `grace.db`, `skills/`).

В handoff перечисли реальные workflow triggers, permissions, timeouts и команды. Не читай/не копируй `.env.production` и не печатай секреты.
