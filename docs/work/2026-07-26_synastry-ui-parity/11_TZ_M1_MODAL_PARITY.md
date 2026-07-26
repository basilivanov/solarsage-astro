# 11_TZ (M1): добивка модалок синастрии до pixel-perfect

## 1. Packet title
React modal parity: клик по линии колеса открывает drill-down; заголовок drill-down — тех-сигнатура; финальные мелочи модалок.

## 2. Phase / Wave
W-SYNASTRY-MVP, modal parity. Эталон — ИСПРАВЛЕННЫЙ макет (ветка prototype/synastry-html@26d18ec5; скриншоты приёмки: `artifacts/proto-walk/f01-modal-aspect.png`, `f04-modal-denis-combined.png`, `f05-add-unknown.png`).

## 3. Modules
- `components/synastry/synastry-wheel.tsx` (line click → open drilldown)
- `components/synastry/synastry-detail-screen.tsx` (связка wheel→sheet)
- `components/synastry/aspect-drilldown-sheet.tsx` (header order)

## 4. Goal

### 4.1. Wheel line click → drill-down (как в макете)
- В исправленном макете клик по линии аспекта в колесе ОТКРЫВАЕТ модалку (`line.onclick = openAspectMeaning(index)`).
- У нас сейчас: line click только select/highlight. Изменить: клик по линии = select (подсветка, как сейчас) + открытие `AspectDrilldownSheet` по aspectId линии. После закрытия sheet линия остаётся выбранной (уже есть).
- Hit-area и aria уже есть (P3b); aria-label не менять.

### 4.2. Drill-down header order (точно как макет)
Макет: eyebrow «АСТРОЛОГИЧЕСКИЙ КОНТАКТ», H1 Georgia = тех-сигнатура «Луна △ Венера»; hero-плашка = tone-квадрат с символом + HEADLINE + meta («Тригон · орб 1°12′ · поддерживающий контакт»).
У нас сейчас: H1 = headline, а тех-сигнатура в плашке. Поменять местами:
- H1 (Georgia, ~24-27px) = локализованная тех-сигнатура (`{ownerPlanet.label} {aspectSymbol} {partnerPlanet.label}`).
- В hero-плашке на месте тех-строки — headline (крупно, sans 22px как в макете `.aspect-modal-hero h2`).

### 4.3. Сверить section titles и мелочи с исправленным макетом
- «ЧТО ИМЕННО СОЕДИНЯЕТСЯ», «КАК РАБОТАЕТ {КВАДРАТ}» (kind uppercase по-русски), «КАК ЭТО ПРОЯВЛЯЕТСЯ В ЖИЗНИ», «ЧТО ПОМОГАЕТ», «ВАЖНО: ЭТО НЕ ОЗНАЧАЕТ» — выровнять наши подписи точно.
- planet cards: «КАРТА ПАРТНЁРА · {ИМЯ}» (uppercase owner label) — проверить наличие имени.
- «Понятно» CTA — `.primary full` (plum, radius 17, padding 15px 18px, Inter 16px/760).

## 5. Exact write scope
- `components/synastry/synastry-wheel.tsx`
- `components/synastry/synastry-detail-screen.tsx`
- `components/synastry/aspect-drilldown-sheet.tsx`
- `__tests__/synastry/synastry-wheel.test.tsx`, `__tests__/synastry/aspect-drilldown-sheet.test.tsx`
- `e2e/mock-visual/synastry-detail.spec.ts` (кейс: click line → sheet открыт) + snapshots

## 6. Frozen / Out of scope
- Геометрия/зодиак колеса, список, add sheet (принят в X2), backend.
- Тексты данных (LLM) не менять.

## 7. Must-preserve invariants
- Selection state wheel остаётся controlled (P3b); aria/keyboard contract линий и планет.
- data-testid: `synastry-wheel`, `synastry-aspect`, sheet root/testids не переименовывать.
- Все существующие тесты зелёные.

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/synastry-detail.spec.ts
```

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок + e2e кейс «line click → drilldown открыт».

## 10. Escalation rule
Нужен backend/wheel geometry/list scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
