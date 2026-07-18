# R10D — architect-approved visual baseline refresh

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

## Решение архитектора

Expected/actual визуально проверены. Новый actual — намеренный дизайн: три подробных горизонта, human-first объяснения, периоды/пики, жизненные проявления, опоры/риски, действия/anti-actions и ссылки в 12 сфер. Обновление baseline одобрено.

## Scope

Изменять только active visual baselines/review assets и удалять доказанно unreferenced legacy snapshots:

```text
e2e/mock-visual/day-v2.spec.ts-snapshots/
docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/
```

Product code/spec logic не менять.

## Шаги

1. Запустить direct preview:

```bash
node e2e/mock-visual/start-v2-preview.mjs
```

2. Bounded readiness HTTP 200.
3. Explicit approved update:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
UPDATE_SNAPSHOTS=true \
pnpm exec playwright test e2e/mock-visual/day-v2.spec.ts --project=chromium --project=mobile
```

4. Завершить preview TERM, дождаться bounded exit, убедиться что `next-env.d.ts` и `tsconfig.json` clean.
5. Удалить только legacy snapshot files, если `rg` доказывает отсутствие имён в active specs:

```text
01-human-first-overview-mobile-mobile-linux.png
02-work-sphere-expanded-mobile-mobile-linux.png
03-why-human-and-astro-expanded-mobile-mobile-linux.png
04-full-day-human-first-mobile-mobile-linux.png
```

6. Повторно запустить тот же spec с `UPDATE_SNAPSHOTS` unset/false для обоих projects. Acceptance = pass, никакого создания baseline.

## Проверки

- active 3 screenshot names × 2 projects = 6 snapshot files;
- review assets 01/02/03 актуальны;
- no legacy filenames referenced;
- fail-closed rerun passes;
- `git status --short next-env.d.ts tsconfig.json` empty;
- ports 3003/18092 free;
- `git diff --check` clean.

Не commit/push/live production actions. Не читать `.env.production`.
