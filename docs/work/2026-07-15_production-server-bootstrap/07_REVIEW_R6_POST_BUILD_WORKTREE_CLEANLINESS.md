# Review R6 — keep the production worktree clean after Next build

Дата: 2026-07-15

## Контекст live rollout

После успешного `pnpm build` production server получил tracked diff:

```diff
-import "./.next/types/routes.d.ts";
+import "./.next-prod/types/routes.d.ts";
```

Это ожидаемая генерация Next.js: `resolveNextDistDir()` выбирает `.next-prod` при `NODE_ENV=production`. Но следующий routine deploy запускает fail-closed clean-worktree preflight и поэтому остановится. Ручной `git restore` после каждого deploy недопустим.

## Границы

Разрешено менять только:

```text
scripts/prod-deploy.sh
docs/PRODUCTION_RUNBOOK.md
```

Не менять `next-env.d.ts`, Next config, `resolveNextDistDir`, package scripts, frontend code или `.gitignore`. Не коммитить generated churn. Commit/push/server mutations запрещены. Существующие R3–R5 изменения сохранить.

## Требуемая deploy-логика

В `scripts/prod-deploy.sh` после успешного production build и до Python preflight/database stages добавить fail-closed cleanup block.

### Разрешённая generated-форма

Изменённый `next-env.d.ts` можно автоматически восстановить только если его полное содержимое после build exact равно:

```ts
/// <reference types="next" />
/// <reference types="next/image-types/global" />
import "./.next-prod/types/routes.d.ts";

// NOTE: This file should not be edited
// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.
```

Нельзя принимать произвольный файл только по grep одной строки. Нужна exact full-content equality, чтобы не затереть пользовательское или вредоносное изменение.

### Алгоритм

1. До build clean-worktree gate уже гарантирует отсутствие tracked diff; сохранить этот контракт.
2. После `pnpm build`:
   - если `next-env.d.ts` не изменён, ничего не делать;
   - если изменён и exact совпадает с разрешённой generated-формой, восстановить только `next-env.d.ts` из текущего `HEAD` (`git restore --source=HEAD --worktree -- next-env.d.ts`) и вывести короткое безопасное сообщение;
   - если изменён, но full content отличается, завершить deploy non-zero с понятной ошибкой, ничего не восстанавливая;
   - после допустимого восстановления повторно проверить весь tracked worktree и index;
   - если build изменил любой другой tracked файл или оставил staged changes, завершить deploy non-zero и вывести только список путей через `git status --short` (не содержимое diff).
3. Untracked build artifacts (`.next-prod`) не должны ломать gate; проверяется tracked diff/index. Существующие ignore rules не менять.

Не использовать `git reset`, `git checkout -- .`, `git clean`, wildcard restore или восстановление нескольких файлов. Не маскировать неожиданные изменения.

Вынести логику в небольшую bash-функцию с `START_FUNCTION_CONTRACT`, если это делает тестирование/читаемость лучше; не устраивать общий рефакторинг deploy script.

## Runbook

В `docs/PRODUCTION_RUNBOOK.md` кратко зафиксировать:

- Next production build генерирует `.next-prod` и временно обновляет `next-env.d.ts`;
- deploy script автоматически восстанавливает только exact известную generated-форму;
- любой другой tracked post-build diff является fail-closed ошибкой;
- оператор не должен добавлять `next-env.d.ts` в commit и не должен обходить gate через broad restore/reset.

## Проверки

Минимум:

```bash
bash -n scripts/prod-deploy.sh
git diff --check
git status --short
```

Добавить безопасную локальную regression-проверку логики без запуска полного deploy, без чтения production env и без server mutations. Допустимые варианты:

- выделить чистую helper-функцию в отдельный shell library/test harness; или
- извлечь только function definition из script в temporary harness.

Regression должна доказать три сценария в temporary git repo/worktree:

1. exact generated `.next-prod` content → файл восстановлен к HEAD, exit 0, tracked worktree clean;
2. unexpected edit в `next-env.d.ts` → non-zero, edit сохранён;
3. exact generated `next-env.d.ts` плюс изменение другого tracked файла → non-zero, другое изменение не затёрто.

Если добавляется отдельный test script, сначала согласовать его необходимость с минимальным scope; предпочтительнее компактный inline temporary harness в handoff, без нового tracked файла.

Также выполнить architect-friendly static assertions:

```bash
grep -F 'git restore --source=HEAD --worktree -- next-env.d.ts' scripts/prod-deploy.sh
! grep -E 'git (reset|clean)|git (checkout|restore).*(-- |\*)' scripts/prod-deploy.sh
```

Вторая проверка должна быть адаптирована так, чтобы разрешённая exact restore-команда не дала ложное срабатывание.

## Handoff

Вернуть exact diff scope, результаты трёх regression-сценариев, `bash -n`, `git diff --check`, подтверждение отсутствия generated `next-env.d.ts` diff, commit/push/server mutations. После handoff остановиться.
