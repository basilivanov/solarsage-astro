# Finalization instructions — accepted three-horizon Why preview

Статус архитектурного ревью: **ACCEPTED**

## 1. Scope финального staging

В implementation commit разрешено включить только файлы этой задачи:

- `components/today/why-time-horizon-card.tsx`;
- `components/today/why-expanded.tsx`;
- `lib/presentation/today-v2.ts`;
- `__tests__/lib/presentation/today-v2.test.ts`;
- `__tests__/components/TodayScreen.v2-downstream.test.tsx`;
- `e2e/mock-visual/day-v2.spec.ts`;
- `e2e/mock-visual/fixtures/day-v2-2026-07-08.ts`;
- `e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json`;
- шесть новых `three-horizons` PNG snapshots в
  `e2e/mock-visual/day-v2.spec.ts-snapshots/`;
- `docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/00_TZ.md`;
- `02_arch_review.md`;
- `03_arch_review_followup.md`;
- `04_finalization.md`;
- три PNG в `assets/`.

Не добавлять:

- `.grace/`;
- `artifacts/design/`;
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`;
- `grace.db`;
- `skills/`;
- любые другие unrelated файлы.

Перед commit проверить `git diff --cached --name-only` и `git diff --cached --check`.

## 2. Implementation commit

Создать commit:

```text
feat(today): add three-horizon personal why story
```

Сохранить полный SHA как `implementation_commit`.

## 3. Report

После implementation commit создать:

`docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/01_report.md`

Report должен содержать:

- branch и baseline `386d211bfef6148fa3d3207d280771de91c42ae3`;
- `implementation_commit`;
- продуктовую модель long/medium/fast;
- representative selection:
  - long: annual profection + firdar major;
  - medium: Pluto trine Saturn + Neptune opposition Saturn;
  - fast: Moon opposition Pluto;
- safe standalone/empty/legacy fallback behavior;
- glossary/target-type safety;
- список изменённых файлов;
- review assets;
- проверки:
  - scoped Vitest: 2 files / 33 tests;
  - full Vitest reviewer gate: 91 files / 954 tests;
  - `npx tsc --noEmit`;
  - `git diff --check`;
  - mobile Playwright update + no-update;
  - preview 3003 -> 200;
- production untouched;
- main/merge untouched;
- known unrelated untracked untouched.

Затем создать отдельный commit:

```text
docs: report three-horizon why preview
```

Сохранить полный SHA как `report_commit`.

## 4. Push

После обоих commit:

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
```

Проверить, что `git ls-remote` для remote branch совпадает с локальным `HEAD`.

Не создавать PR, не merge/rebase, не переключать ветку, не трогать production.
Preview оставить работающим на `3003`.

## 5. Финальный callback

```text
DONE_THREE_HORIZON_WHY_PREVIEW
branch: preview/solarsage-v2-human-first-navigator-ux
implementation_commit: <full sha>
report_commit: <full sha>
remote_head: <full sha>
preview_url: http://127.0.0.1:3003/day/2026-07-08?why=1
tests: scoped 33; full 954; tsc; Playwright mobile update+verify; curl 200
screenshots: <three docs/work asset paths>
production_untouched: YES
main_merge_untouched: YES
known_untracked_untouched: YES
push: DONE
```

После callback остановиться.
