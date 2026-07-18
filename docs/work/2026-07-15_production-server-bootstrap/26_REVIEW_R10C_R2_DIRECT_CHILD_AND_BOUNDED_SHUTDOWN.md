# Review R10C-R2 — direct child PID and bounded shutdown

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

## Проблема

Harness запускал `pnpm preview:v2 &` и посылал signal PID оболочки pnpm. Node preview не завершился сразу; restore произошёл только после внешнего 120s timeout. Visual workflow использует тот же pattern и может зависать до job timeout.

## Исправления

### 1. Preview launcher должен spawn direct Next child

В `start-v2-preview.mjs` не spawn `pnpm exec next`. Запусти Next CLI напрямую через текущий Node:

```js
spawn(process.execPath, [join(ROOT, "node_modules/next/dist/bin/next"), "dev", ...])
```

Проверить, что CLI file существует как regular file до mock listen/spawn; fail-safe message без secret/path traversal. Тогда `next.pid` — реальный контролируемый child.

### 2. Bounded shutdown state machine

- На SIGINT/SIGTERM: send SIGTERM direct child.
- Дождаться `exit` child; max 5s.
- Если не вышел — send SIGKILL и bounded wait ещё до 2s.
- Только после child exit/forced termination закрыть mock server, затем восстановить `next-env.d.ts` и `tsconfig.json`, затем `process.exit(code)`.
- Никакого fixed 500ms restore пока child ещё может писать.
- `error` event spawn также ведёт в finalize/restore.
- Finalize exactly once.

### 3. Workflow PID

В `.github/workflows/visual-regression.yml` запускай direct:

```bash
node e2e/mock-visual/start-v2-preview.mjs >... &
```

PID file теперь содержит Node preview PID. Cleanup `kill` + bounded poll/wait; если TERM не завершил, KILL. Не использовать pnpm wrapper для background lifecycle.

### 4. Exactness cleanup

- Используй `basename()` из `node:path` в atomic helper, не `join(...).split('/')`.
- Для tsconfig require each generated include entry встречается ровно один раз.
- Для next-env candidates сравни exact bytes; если поддерживаешь LF/CRLF, сформируй четыре exact Buffer candidates, а не normalize partial/string includes.

## Test

Запускать Node direct, без Git restore:

```bash
sha256sum next-env.d.ts tsconfig.json > /tmp/before
node e2e/mock-visual/start-v2-preview.mjs >/tmp/preview.log 2>&1 & pid=$!
# bounded curl 200
kill -TERM "$pid"
# bounded wait <= 10s; process must disappear
sha256sum next-env.d.ts tsconfig.json > /tmp/after
cmp /tmp/before /tmp/after
! kill -0 "$pid" 2>/dev/null
git status --short next-env.d.ts tsconfig.json
```

Проверить ports 3003/18092 free after exit. Не запускать screenshot update, не commit/push/live production, не читать env.
