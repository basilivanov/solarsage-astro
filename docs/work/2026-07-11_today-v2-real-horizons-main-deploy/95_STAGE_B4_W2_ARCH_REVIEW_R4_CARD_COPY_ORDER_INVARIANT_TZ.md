# Stage B4.W2 architectural review R4 — exact backend copy/order invariant

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый SHA: `c0c86c540a1d8f77b282ff21705758c8594d5a6e`
Предыдущие ТЗ: `91`–`94`
Статус: **ONE-LINE CONTRACT CORRECTION — NO COMMIT / NO PUSH**

## 1. Принято

Production behavior, tests и все R3 cleanup‑изменения приняты. Не менять JSX,
copy, layout, className, selection, timing, filtering, ARIA или tests.

## 2. Единственный обнаруженный разрыв

В `94_STAGE_B4_W2_ARCH_REVIEW_R3_FINAL_CONTRACT_CLEANUP_TZ.md` для
`components/today/why-time-horizon-card.tsx` явно требовался invariant о том,
что backend copy и backend array order сохраняются дословно. В текущем
`START_MODULE_CONTRACT` остальные invariants присутствуют, но этого отдельного
invariant нет.

## 3. Единственное разрешённое изменение

Allowlist — ровно один файл:

~~~text
components/today/why-time-horizon-card.tsx
~~~

В существующий список `invariants` модуля добавить ровно одну смысловую строку,
например:

~~~text
//   - backend human copy and backend array order are preserved exactly; frontend does not rewrite, sort, or infer them.
~~~

Формулировка может быть грамматически выровнена с соседними строками, но должна
однозначно фиксировать обе части:

- backend human copy выводится exact, без переписывания/сокращения;
- backend arrays выводятся exact order, без сортировки/reselection/inference.

Никаких других изменений, включая перестановку комментариев, не делать.

## 4. Проверки

~~~bash
git diff --check
git diff --name-only
git diff --cached --name-only
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
pnpm typecheck
~~~

Ожидания:

- общий W2 diff остаётся exact 8 tracked implementation/test paths;
- текущая R4‑правка затрагивает exact 1 path;
- index пуст;
- generated diff пуст;
- typecheck PASS;
- commit/push не выполнять;
- B4.W3 не начинать.

## 5. Запрещено

- менять runtime или tests;
- менять файлы вне exact one-file allowlist;
- git add/commit/push;
- запускать/перезапускать сервисы или preview 3003;
- использовать субагентов.

## 6. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W2_R4
changed_now: EXACT_1_COMMENT_ONLY
runtime_behavior: UNCHANGED
card_backend_copy_order_invariant: EXPLICIT
typecheck: PASS
git_diff_check: PASS
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
