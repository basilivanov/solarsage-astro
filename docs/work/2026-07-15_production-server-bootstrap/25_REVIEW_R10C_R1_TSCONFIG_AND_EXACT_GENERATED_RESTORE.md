# Review R10C-R1 — tsconfig cleanup and exact generated restore

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

## Блокеры

1. Next dev добавляет UID-cache paths не только в `next-env.d.ts`, но и в tracked `tsconfig.json`; после preview он остаётся dirty.
2. Тест очистил `tsconfig.json` через запрещённый `git restore`, поэтому auto-clean contract не доказан.
3. `next-env.d.ts` сейчас считается expected через `includes`, что может перезаписать файл с дополнительными неожиданными изменениями. Нужен byte-exact match.

## Исправления

### 1. Generic original-state capture

До spawn сохрани в памяти bytes + mode отдельно для:

```text
next-env.d.ts
tsconfig.json
```

### 2. Exact `next-env.d.ts` recognition

Сформируй exact candidate bytes (с точными newline и финальным newline) для обоих реально допустимых generated imports:

```text
./<distDir>/types/routes.d.ts
./<distDir>/dev/types/routes.d.ts
```

Восстанавливай original только если current bytes полностью равны одному candidate. Не `includes`, не regex partial match. Unexpected -> warning, no overwrite.

### 3. Semantic-exact `tsconfig.json` recognition

`tsconfig.json` — valid JSON. Parse original и current. Допустимое generated изменение только одно:

- current object во всём deep-equal original;
- `include` дополнен ровно двумя UID-cache строками (обычный + `/dev/`), без удаления/reorder/изменения любых original entries/keys:

```text
<distDir>/types/**/*.ts
<distDir>/dev/types/**/*.ts
```

Если это единственный diff — атомарно восстановить exact original bytes/mode. Любой иной diff/parse failure -> warning и оставить файл.

Не использовать `git restore/reset/checkout/clean` ни в реализации, ни в harness.

### 4. Atomic helper and cleanup

- Общий helper temp-in-same-directory + rename;
- temp cleanup on write/rename failure;
- safe basename regex должен быть strict, например `^\.next-v2-preview-[A-Za-z0-9_-]+$`; legacy `.next-v2-preview` override не принимать;
- directory access check включает `R_OK | W_OK | X_OK`.

### 5. Tests

Без Git restore:

1. Сохрани hashes/bytes `next-env.d.ts`, `tsconfig.json` во временные файлы вне repo.
2. Запусти preview, дождись HTTP 200 bounded.
3. SIGINT, дождись полного exit.
4. `cmp` обоих tracked files с сохранёнными originals = 0.
5. `git status --short next-env.d.ts tsconfig.json` пуст.
6. Selected dist dir owner = current user.

Playwright screenshot mismatch сейчас отдельный fail-closed baseline result; не обновляй snapshots в этой задаче. Достаточно structural/curl proof и clean tracked files.

Проверки:

```bash
node --check e2e/mock-visual/start-v2-preview.mjs
git check-ignore .next-v2-preview-1001/
git diff --check
```

Не commit/push/live production actions. Не читать `.env.production`.
