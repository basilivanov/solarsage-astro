# R10C — astro-owned preview cache and clean exit

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

## Причина

Локальный `pnpm preview:v2` на 3003 упал с Turbopack `Permission denied`: старый `.next-v2-preview` содержал root-owned files. Пользователь требует, чтобы preview всегда запускался от `astro` без sudo/chown/manual cleanup.

## Scope

Измени:

```text
e2e/mock-visual/start-v2-preview.mjs
e2e/mock-visual/README.md
.gitignore
```

При необходимости добавь test-only unit/script test рядом с harness. Product/runtime paths не менять.

## Требования

### 1. User-specific disposable dist dir

- Не использовать общий fixed `.next-v2-preview` по умолчанию.
- Выбрать безопасный user-specific relative dist dir, например `.next-v2-preview-${process.getuid()}`.
- Root и astro автоматически получают разные cache paths; существующий root-owned `.next-v2-preview` не должен читаться/изменяться/удаляться.
- Разрешить optional `NEXT_DIST_DIR` override только если это безопасный repository-relative basename из preview namespace; reject absolute path, `..`, slash/backslash traversal и произвольные product dirs.
- Добавить ignore pattern `.next-v2-preview-*/` (старый `.next-v2-preview/` оставить ignored для legacy cleanup).
- Перед spawn проверить, что выбранный dir отсутствует либо writable/traversable текущим UID; при проблеме fail-fast с безопасным сообщением, без sudo suggestion.

### 2. Restore `next-env.d.ts` byte-safely

Next dev меняет tracked `next-env.d.ts`. Preview launcher должен:

1. До spawn сохранить original bytes/status файла в памяти.
2. На normal shutdown, SIGINT, SIGTERM и child failure прочитать current bytes.
3. Восстановить original bytes только если current bytes точно совпадают с известным generated Next format для выбранного dist dir (`./<dist>/dev/types/routes.d.ts` или реально наблюдаемый формат).
4. Если current bytes отличаются неожиданно, не перетирать; вывести warning и оставить файл для manual review.
5. Восстановление должно быть atomic temp-in-same-dir + rename, с исходным mode по возможности.
6. Не использовать `git restore/reset/checkout/clean` и не трогать другие files.

Если Next не менял файл — ничего не писать.

### 3. Lifecycle

- Сохранить ports 18092/3003, mock API no-fallthrough и SIGTERM child cleanup.
- Shutdown должен дождаться/ограниченно завершить Next, затем восстановить `next-env.d.ts`, затем exit.
- Не создавать root-owned files и не вызывать sudo.
- Логи не должны содержать secrets.

### 4. README

Документировать, что preview использует isolated user-owned cache и автоматически убирает только ожидаемую generated правку `next-env.d.ts`; unexpected edits не перезаписываются.

## Проверки

Без удаления legacy root cache:

```bash
node --check e2e/mock-visual/start-v2-preview.mjs
git check-ignore .next-v2-preview-1001/
git diff --check
```

Затем локально от `astro`:

1. Запустить `pnpm preview:v2`.
2. Bounded curl на `http://127.0.0.1:3003/day/2026-07-08` должен вернуть 200.
3. Запустить `E2E_BASE_URL=http://127.0.0.1:3003 CI=true pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=chromium` без snapshot update.
4. SIGINT preview.
5. `git status --short next-env.d.ts` пуст; selected dist dir owned current user.

Не commit/push/live production actions. Не читать `.env.production`.
