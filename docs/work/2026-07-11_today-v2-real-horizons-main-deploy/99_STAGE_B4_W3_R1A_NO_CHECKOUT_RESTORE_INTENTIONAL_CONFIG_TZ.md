# Stage B4.W3 R1A safety correction — no checkout, restore intentional tsconfig diff

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый SHA: `ae62ad8ced1865cef2b2b1b3a0382d2e06065ce0`
Authority: `97`, `98`
Статус: **IMMEDIATE SAFETY CORRECTION — CONTINUE R1 AFTER REPAIR**

## 1. Подтверждённое нарушение

Во время R1 был выполнен:

~~~bash
git checkout -- next-env.d.ts tsconfig.json
~~~

Это запрещено ТЗ и сняло intentional W3 change из `tsconfig.json`. До команды
`tsconfig.json` не содержал чужих правок: его W3 diff был ровно двумя принятыми
real-preview globs. Тем не менее broad checkout больше не использовать.

## 2. Немедленные действия

1. Если текущий proof launcher ещё запущен:
   - использовать только сохранённый launcher PID;
   - отправить SIGTERM этому parent;
   - `wait` его;
   - доказать отсутствие listener 3003;
   - не использовать `pkill`, killall или поиск/kill чужих процессов.
2. Проверить `next-env.d.ts`:
   - он должен exact совпадать с HEAD (`.next/types/routes.d.ts`);
   - если launcher уже корректно restored — не менять;
   - если нет — вернуть точным `apply_patch`, не checkout.
3. Вернуть intentional `tsconfig.json` W3 diff только через `apply_patch`:

~~~json
".next-v2-preview/dev/types/**/*.ts",
".next-v2-real-preview/types/**/*.ts",
".next-v2-real-preview/dev/types/**/*.ts"
~~~

Остальной файл exact HEAD. Не переставлять другие строки.

## 3. Proof после repair

~~~bash
git diff -- tsconfig.json next-env.d.ts
git status --short -- tsconfig.json next-env.d.ts
ss -ltnp '( sport = :3003 )'
~~~

Ожидания:

- `tsconfig.json` diff — ровно две added real-preview globs;
- `next-env.d.ts` clean;
- 3003 free до нового managed proof;
- никакого другого config diff.

## 4. Продолжение R1

После repair продолжить `98` буквально. В частности:

- launcher должен сам сохранять tracked config clean while running;
- actual smoke/E2E не может использовать checkout/reset для подготовки;
- candidate build cleanup — только exact `apply_patch`;
- config paths нельзя снова менять, кроме уже принятого exact tsconfig diff;
- package/.gitignore accepted diffs сохраняются.

Managed background shell с сохранённым PID допустим только если процесс всегда
завершается SIGTERM + wait в этой wave. `nohup`, detached shell daemon и orphan
запрещены.

## 5. Запрещено

~~~text
git checkout -- <path>
git restore <path>
git reset
git clean
git add/commit/push
pkill/killall
~~~

Не переписывать docs `97`–`99`.

## 6. Callback addition

К callback `98` добавить:

~~~text
checkout_violation_repaired: YES_EXACT_PATCH
intentional_tsconfig_diff: EXACT_2_GLOBS
next_env_after_proof: CLEAN
broad_destructive_git_after_r1a: ZERO
~~~

После полного callback `98` остановиться.
