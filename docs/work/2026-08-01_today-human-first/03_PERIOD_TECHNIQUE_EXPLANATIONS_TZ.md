# Packet: concise period technique explanations

## Phase / Wave

`W-TODAY-HUMAN-FIRST / P3-PERIOD-EXPLANATIONS`

## Modules

- `M-SPHERE-PAGE`
- `M-TODAY-IMPULSE-DRILLDOWN`
- новый `M-PERIOD-TECHNIQUE-COPY`

## Goal

Сохранить технические названия «профекция», «соляр», «фирдар», но рядом кратко и детерминированно объяснить: что это за техника, как она задаёт текущий фон и что человек может замечать в реальной жизни.

## Exact Write Scope

- `components/today-convergence/period-technique-copy.ts` (new)
- `components/today-convergence/sphere-page.tsx`
- `components/today-convergence/impulse-drilldown-sheet.tsx`
- `__tests__/components/today-convergence/sphere-page.test.tsx`
- `__tests__/components/today-convergence/today-screen.test.tsx`

## Frozen / Out Of Scope

- Не менять API, generated contracts, расчёт периодов или их сроки.
- Не переименовывать техники и не скрывать исходный `item.title`.
- Не делать персональные выводы сверх переданных title/sphere/natal facts.
- Не менять navigator/layout/HowCalculated, e2e baselines или screenshots.
- Не трогать unrelated/untracked files.

## Must Preserve Invariants

- Registry исчерпывающе покрывает `annual_profection`, `solar_return`, `firdar_major`, `firdar_minor`.
- В UI остаётся исходное название периода и точная дата окончания.
- Для каждого периода видны три коротких смысловых части: `Что это`, `Как влияет сейчас`, `Что можно заметить`; тексты статические, ясные, без обещаний и нейро-слопа.
- Пояснения одинаковы на полной странице сферы и в impulse modal.
- Отсутствующий/будущий enum обрабатывается честным нейтральным fallback, не роняет экран.
- Стабильные test ids и `data-technique` остаются/добавляются; GRACE карты актуальны.

## Verification Command

```bash
cd /opt/solarsage-astro && npx vitest run __tests__/components/today-convergence/sphere-page.test.tsx __tests__/components/today-convergence/today-screen.test.tsx
```

## Expected Evidence

- Список файлов и пример copy для всех техник.
- Targeted vitest output.
- Подтверждение, что исходные titles/dates сохранены и API не менялся.

## Escalation Rule

Если требуется новый API-факт, изменение enum или файл вне scope — остановиться и доложить архитектору; не расширять packet самостоятельно.

## No Commit Rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
