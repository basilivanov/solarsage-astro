# Review R10B-R2 — secret injection and real-suite boundary

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: финальная correction R10B; commit/push/live deploy запрещены.

## 1. Не вставлять secrets expressions в shell source

В `.github/workflows/e2e.yml` сейчас внутри `run: |` есть:

```bash
export TELEGRAM_BOT_TOKEN="${{ secrets.E2E_TELEGRAM_BOT_TOKEN }}"
export OPENROUTER_API_KEY="${{ secrets.E2E_OPENROUTER_API_KEY }}"
```

Это нарушает workflow shell-injection contract. Передай secrets только через step-level `env:`:

```yaml
env:
  E2E_TELEGRAM_BOT_TOKEN: ${{ secrets.E2E_TELEGRAM_BOT_TOKEN }}
  E2E_OPENROUTER_API_KEY: ${{ secrets.E2E_OPENROUTER_API_KEY }}
```

В shell используй только quoted variables `"$E2E_..."`. Ни одного `${{ secrets.* }}` внутри `run` source.

## 2. Исключить secrets из всех frontend children

И `pnpm run build`, и `pnpm exec next start` не должны наследовать `E2E_TELEGRAM_BOT_TOKEN`, `E2E_OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`. Используй `env -u ...` или отдельный очищенный subshell для обоих команд. API process и Playwright generator получают secrets scoped.

## 3. Full real suite не должен включать mock visual

`pnpm exec playwright test --project=chromium` рекурсивно подхватывает `e2e/mock-visual`. Это нарушает separation real E2E vs routed fixtures.

Для full запускай только top-level real specs, например:

```bash
pnpm exec playwright test e2e/*.spec.ts --project=chromium
```

Проверь shell expansion и синхронизируй runbook: full = all top-level real specs, mock visual остаётся отдельным manual workflow.

## 4. Minor robustness

- HMAC test formatting: blank line between top-level test functions; subprocess env can retain safe `PATH`/locale via `{**os.environ, "TELEGRAM_BOT_TOKEN": synthetic}` while explicitly proving no token output, либо оставить absolute interpreter if deliberate and documented.
- Не менять runtime/product code.

## Проверки

```bash
python3 - <<'PY'
import yaml
yaml.safe_load(open('.github/workflows/e2e.yml'))
print('yaml_ok')
PY
! rg -n '\$\{\{ secrets\.' .github/workflows/e2e.yml --glob '*.yml' | rg 'run|export' || true
rg -n 'playwright test e2e/\*\.spec\.ts --project=chromium' .github/workflows/e2e.yml
git diff --check
```

Не читать/копировать настоящий `.env.production`; synthetic fixtures only. Не commit/push/live actions.
