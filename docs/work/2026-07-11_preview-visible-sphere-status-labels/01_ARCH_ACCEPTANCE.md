# Архитектурная приёмка — видимые статусы 12 сфер

Дата: 2026-07-11
Вердикт: `ACCEPTED_FOR_LOCAL_PREVIEW`
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Commit/push: не выполнялись.

## Принятое отображение

| Verdict | Плитка | Раскрытый блок |
|---|---|---|
| `good` | `Поддержка` | `Поддерживающий фон` |
| `neutral` | `Ровно` | `Нейтральный фон` |
| `caution` | `Внимание` | `Требует внимания` |
| `avoid` | `Отложить` | `Высокое напряжение · лучше отложить` |

Статус теперь видим текстом и не зависит только от цветной точки. Compact row,
compact status, details root и details badge имеют стабильный нормализованный
`data-status` contract. Unknown verdict безопасно нормализуется в `neutral`.

На fixture раскрытая сфера показывает:

```text
Работа и статус
Требует внимания

Что может проявиться
В этой сфере сегодня особенно важны точность и отсутствие спешки.

Что поможет
Не форсируйте разговор о статусе — сначала отделите принципиальное от реакции на давление
```

## Независимые проверки архитектора

```text
Vitest: TodayScreen V2 downstream — 11 passed
TypeScript: npx tsc --noEmit — passed
Diff: git diff --check — passed
Playwright mobile: timing fixture + visible sphere status — 2 passed
Preview 3003: alive
```

Review screenshot:

```text
docs/work/2026-07-11_preview-visible-sphere-status-labels/assets/01-work-status-expanded-mobile.png
```

Production services, auth, API, timing fixture и Why не менялись.
