# Stage 1.W0 architect errata R1 — Next 16 dev types and generated-dist cleanup

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Parent: `104_STAGE_1_W0_STRICT_HARNESS_STABILIZATION_TZ.md`
Статус: **AUTHORIZED NARROW CORRECTION INSIDE W0 — NO COMMIT / NO PUSH**

## 0. Причина errata

Managed smoke фактически доказал поведение установленного Next `16.2.6`:

~~~text
NEXT_DIST_DIR=.next-v2-real-preview
next dev
=> import "./.next-v2-real-preview/dev/types/routes.d.ts";
~~~

В разделе 4.4 ТЗ `104` ошибочно был записан путь без сегмента `/dev`.
Из-за этого fail-closed classifier корректно признал реальный generated-файл
неизвестным и сохранил его. Это ошибка архитектурного ТЗ, а не повод ослаблять
classifier.

Эта errata заменяет только конфликтующие детали `104`. Всё остальное в `104`
остаётся обязательным.

## 1. Allowlist и запреты не меняются

Implementation allowlist остаётся ровно семь путей:

~~~text
.gitignore
package.json
tsconfig.json
scripts/preview-v2-real.mjs
__tests__/scripts/preview-v2-real.test.ts
e2e/real-v2-preview.spec.ts
e2e/README.md
~~~

`next-env.d.ts` не является implementation path и обязан завершить волну без
diff. Разрешено только узкое восстановление текущего доказанно generated
содержимого по разделу 3 этой errata.

По-прежнему запрещены:

~~~text
git checkout / restore / reset
git show redirect
Python или shell file rewrite
правки next.config.mjs, eslint.config.mjs, backend, product, contracts, lockfile
расширение classifier дополнительными приблизительными вариантами
commit / push / следующая волна
~~~

## 2. Единственный точный generated declaration

Исправить `buildGeneratedNextEnv` и поведенческие тесты так, чтобы единственным
принимаемым generated-вариантом был фактический вывод Next dev:

~~~text
/// <reference types="next" />
/// <reference types="next/image-types/global" />
import "./.next-v2-real-preview/dev/types/routes.d.ts";

// NOTE: This file should not be edited
// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.
~~~

Требования `104` про LF/CRLF, исходный final newline, точное равенство и
`unsafe_user_edit` сохраняются.

Запрещено принимать одновременно `/types/` и `/dev/types/`. Для текущего
`next dev` каноничен только `/dev/types/`; любой иной dist import остаётся
`unsafe_user_edit`.

Обновить тест wrong-dist/wrong-path так, чтобы он отдельно доказывал:

~~~text
.next-v2-real-preview/types/routes.d.ts => unsafe_user_edit
.next-other/dev/types/routes.d.ts       => unsafe_user_edit
~~~

Общее число behavioral tests остаётся не меньше 20.

## 3. Точное восстановление уже оставшегося generated `next-env.d.ts`

До нового smoke сначала проверить, что текущий diff `next-env.d.ts` ровно такой:

~~~diff
-import "./.next/types/routes.d.ts";
+import "./.next-v2-real-preview/dev/types/routes.d.ts";
~~~

и больше никаких изменений в файле нет.

Только после этой проверки разрешён точный `apply_patch`, меняющий одну строку
обратно на:

~~~text
import "./.next/types/routes.d.ts";
~~~

Затем обязательно:

~~~text
git diff -- next-env.d.ts => EMPTY
mode unchanged
~~~

Нельзя получать содержимое через git redirect и нельзя перезаписывать файл
целиком.

## 4. Generated dist и frontend guard

ESLint flat config в этом репозитории сканирует существующий ignored build
directory при `eslint .`; `.gitignore` сам по себе не исключает этот каталог.
Это не разрешает править `eslint.config.mjs`.

Правильный порядок:

1. завершить конкретный managed smoke/E2E;
2. доказать отсутствие listener/descendants на 3003 и 18092;
3. удалить только owned ignored candidate `.next-v2-real-preview`;
4. убедиться, что candidate отсутствует;
5. затем запускать `pnpm guardrails:frontend`;
6. launcher не обязан удалять build cache при каждом штатном shutdown.

Нельзя удалять `.next`, `.next-prod`, `.next-v2-preview` или другие каталоги.

## 5. Повторный managed smoke

После исправления classifier и точного восстановления initial `next-env.d.ts`:

- запустить launcher управляемо;
- дождаться root `200` и `/api/health` `200`;
- пока launcher работает, доказать:
  - `next-env.d.ts` уже восстановлен к initial snapshot и diff пуст;
  - `tsconfig.json` не получил runtime-изменений сверх двух заранее принятых
    tracked glob;
  - 18092 отсутствует;
- отправить launcher SIGTERM и дождаться полного выхода;
- доказать отсутствие listener и descendants;
- снова доказать пустой `next-env.d.ts` diff;
- удалить только `.next-v2-real-preview` перед frontend guard.

Если Next выдаёт любой третий declaration, не добавлять его в classifier:
остановиться и вернуть точное содержимое архитектору.

## 6. Strict E2E остаётся expected-fail

Никаких изменений требований разделов 6–7 `104`:

~~~text
auth 200
day 200
chromium fails only: expected today.v2.1, received today.v1
mobile fails only: expected today.v2.1, received today.v1
no 401 / skip / conditional V1 / interception / mock
~~~

После E2E снова выполнить полный managed cleanup и удалить только owned dist
до frontend guard.

## 7. Gates и callback

Повторить все gates и полный callback из `104`. Дополнительно в callback:

~~~text
next16_actual_generated_import: .next-v2-real-preview/dev/types/routes.d.ts
next16_non_dev_variant_rejected: PASS
preexisting_generated_next_env_exact_patch: PASS_ONE_LINE_ONLY
owned_preview_dist_removed_before_frontend_guard: PASS
~~~

После callback остановиться. Commit/push и S1.W1 запрещены.
