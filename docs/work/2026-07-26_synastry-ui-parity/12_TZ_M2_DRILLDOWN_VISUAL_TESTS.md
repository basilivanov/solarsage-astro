# 12_TZ (M2): e2e visual baseline для drill-down модалки

## 1. Packet title
Synastry drill-down: mock-visual e2e для открытой модалки (структурный контент, wheel-line, error state) + snapshot baseline.

## 2. Phase / Wave
W-SYNASTRY-MVP, test hardening. Контекст: drill-down endpoint был стабом и ломался на живых данных — нужен визуальный baseline, который ловит регресс модалки.

## 3. Modules
- `e2e/mock-visual/synastry-detail.spec.ts` (расширить)
- snapshots

## 4. Goal
В `e2e/mock-visual/synastry-detail.spec.ts` (fixtures уже есть — wheel fixture с planets/aspects от P3b):

1. **Drilldown open (structural)**: click по `[data-testid="synastry-aspect"] >> nth=0` → sheet открыт (`role="dialog"`); проверить: eyebrow «АСТРОЛОГИЧЕСКИЙ КОНТАКТ», локализованная тех-сигнатура в заголовке (НЕ raw id, НЕ английский tech), hero с headline и meta «{kind} · {orb} · {контакт}», секции: карточки планет (2), механика, scenes (≥3 named cards), repairs (нумерованные), not-means (3 chips). Snapshot `synastry-drilldown.png` (маскировать динамический текст LLM при необходимости, структура важнее текста).
2. **Drilldown via wheel line**: click по первой aspect line в `[data-testid="synastry-wheel"] svg [role="button"]` → sheet открыт с тем же aspectId; после закрытия (Escape) линия остаётся выбранной (hot/active state).
3. **Error state**: route aspect endpoint → 500 → в sheet показывается русская ошибка (НЕ английский «Failed to fetch...»), sheet закрывается по Escape/кнопке.
4. Обновить/добавить snapshots; проход стабилен ×2 подряд.

## 5. Exact write scope
- `e2e/mock-visual/synastry-detail.spec.ts`
- `e2e/mock-visual/synastry-detail.spec.ts-snapshots/`

## 6. Frozen / Out of scope
- Production код (всё исправлено и задеплоено), другие spec-файлы.

## 7. Must-preserve invariants
- Существующие кейсы spec'а зелёные.
- Snapshot'ы маскируют динамический текст там, где LLM-контент недетерминирован (структурные ассерты по testid/секциям — обязательны, скриншот — дополнение).

## 8. Verification commands
```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/synastry-detail.spec.ts
```

## 9. Expected evidence
- Вывод прогона ×2; список snapshot-файлов.

## 10. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
