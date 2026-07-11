# Visual baseline repair acceptance — visible sphere statuses

Дата: 2026-07-11
Вердикт: `ACCEPTED_BASELINE_REPAIR`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`

## Причина отдельного checkpoint

Публичные статусы сфер были реализованы и архитектурно приняты раньше:

```text
commit: 5de571a783969f5f26a1cde25c0378e98242388b
acceptance: docs/work/2026-07-11_preview-visible-sphere-status-labels/01_ARCH_ACCEPTANCE.md
```

Но старый full-page visual baseline был сохранён без уже принятого текста:

```text
Внимание
Требует внимания
```

S1.W3 не меняет этот UI, но повторный visual gate обнаружил stale baseline.
Обновление нельзя смешивать с contract commit, поэтому оно выделено в
самостоятельный checkpoint без code changes.

## Независимое доказательство архитектора

- `01-why-three-horizons-mobile.png` и
  `02-why-three-horizons-calculation-mobile.png` визуально pixel-identical
  старым версиям; byte-noise восстановлен из `HEAD` и не коммитится.
- Full-page высота изменилась с `8628` до `8712` px в Playwright snapshot:
  ровно `84 CSS px`.
- Вставка начинается около `y=993` и показывает уже принятые compact/details
  status labels.
- Why-horizon content не изменился.
- Browser gate после нового baseline проходит с `--update-snapshots=none`.

## Разрешённые файлы baseline commit

Только:

```text
docs/work/2026-07-11_preview-visible-sphere-status-labels/02_VISUAL_BASELINE_REPAIR_ACCEPTANCE.md
docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets/03-full-day-three-horizons-mobile.png
e2e/mock-visual/day-v2.spec.ts-snapshots/03-full-day-three-horizons-mobile-mobile-linux.png
```

Никаких TS/TSX/Python/schema/fixture изменений в этот commit не включать.

Commit subject:

```text
test(today): align accepted sphere status visual baseline
```

После commit push только текущей preview branch. Затем вернуть/собрать S1.W3
index и сделать его отдельным commit по своей acceptance.