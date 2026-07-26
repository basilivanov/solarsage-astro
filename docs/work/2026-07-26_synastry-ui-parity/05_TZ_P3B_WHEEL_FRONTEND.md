# 05_TZ (P3b): Синастрия — интерактивная SVG-карта SynastryWheel (frontend)

## 1. Packet title
Synastry UI parity, срез P3b: проектного класса двухкольцевая SVG-карта с реальными longitude, интерактивными планетами и аспектами. Зависит от P2 (detail композиция) и P3a (planet points contract).

## 2. Phase / Wave
W-SYNASTRY-MVP, parity wave. Нормативный документ: `docs/work/2026-07-26_synastry-ui-parity/01_TZ_INTERACTIVE_SVG_WHEEL.md` — ЧИТАТЬ ЦЕЛИКОМ, это главное ТЗ среза; master TZ §7. Reference-паттерны: `components/today/day-chart.tsx` (интерактивность/popover/animation), `components/readings/natal-chart-wheel.tsx` (геометрия), `app/globals.css` (chart-* классы).

## 3. Modules
- `components/synastry/synastry-wheel.tsx` (новый)
- `lib/astro/chart-geometry.ts`, `components/astro/astro-chart-tokens.ts` (новые, shared primitives по §9 wheel-TZ)
- `components/synastry/synastry-detail-screen.tsx` (интеграция в placeholder-зону из P2)

## 4. Goal
Секция «Карта взаимодействия» показывает настоящую двухкольцевую карту по 01_TZ (композиция §3, визуальный язык §4, интерактивность §5-6, единое состояние §7):

1. **Primitives** (§9): `lib/astro/chart-geometry.ts` — longitude→angle, polar coords, arc helpers, collision offsets; `components/astro/astro-chart-tokens.ts` — PLANET_SYMBOLS/COLORS, SIGN_SYMBOLS, ASPECT colors через tone. Существующие карты НЕ мигрировать.
2. **SynastryWheel**: fluid SVG viewBox; зодиакальный ring 12 секторов + glyph, alternating tint; inner ring — планеты владельца, outer — партнёра; позиции по реальному longitude из P3a (НЕ по индексу); collision offsets; center glow + подпись «ТЫ + {name}»; legend (§7.6 master).
3. **Планеты** (§5): disk r 9-11 + transparent hit r 13-16; role=button, tabIndex, Enter/Space, русский aria-label («Твой Марс в Овне», «Марс партнёра в Овне, 5 дом»); click select/deselect; spring-анимация selected (framer-motion, как DayChart); selected подсвечивает связанные линии, остальные dim; animated popover (AnimatePresence) — glyph, «Твоя/Его {планета}», знак, дом если houseReliable, approximate-отметка, короткий смысл планеты в отношениях.
4. **Аспекты** (§6): линия по tone (--syn-good/mid/bad, opacity 0.55-0.65); поверх transparent hit-line strokeWidth 12-16; click выбирает (line ярче/толще, остальные 0.08-0.12, обе planet nodes выделены, карточка аспекта активна — раскрыть список если скрыта); aria-label русский (§6.3); click по aspect card → выбор линии + открытие drilldown по реальному aspectId; после закрытия sheet выбор сохраняется.
5. **Единое состояние** (§7): controlled `SynastryWheelSelection{selectedPlanetId, selectedAspectId}` в detail-screen, wheel — controlled component по API §7 wheel-TZ.
6. **Approximate** (§3.1): дома/ASC партнёра не рисовать, подпись о сниженной точности; planet rings и аспекты остаются.
7. **Нет planet данных** (старые репорты): секция показывает только список аспектов из P2 + пометку, что карта появится после пересчёта (без сломанного пустого SVG).
8. prefers-reduced-motion: без неessential анимаций.

## 5. Exact write scope
- `lib/astro/chart-geometry.ts` (новый)
- `components/astro/astro-chart-tokens.ts` (новый)
- `components/synastry/synastry-wheel.tsx` (новый)
- `components/synastry/synastry-detail-screen.tsx` (интеграция + selection state + связь со списком)
- `__tests__/synastry/synastry-wheel.test.tsx` (новый)
- `e2e/mock-visual/synastry-detail.spec.ts` (новый, по образцу e2e/mock-visual/day.spec.ts: interaction кейсы §10 wheel-TZ) + snapshots

## 6. Frozen / Out of scope
- Backend — принят в P3a, не трогать.
- `components/today/day-chart.tsx`, `components/readings/natal-chart-wheel.tsx` — НЕ мигрировать/не менять (только читать паттерны).
- Drilldown sheet переработка — P4 (открытие по aspectId уже работает из P2).
- Глобальные шрифты/тема.

## 7. Must-preserve invariants
- Все запреты 01_TZ §8 (нет индексных позиц, нет угаданных longitude, нет techSignature как id, нет недостоверных домов).
- data-testid: `synastry-wheel` сохраняется на секции; SVG — `role="img"` с aria-label; aspect cards сохраняют `synastry-aspect` testid.
- Все существующие тесты зелёные; GRACE-разметка.
- Нет третьей несовместимой системы glyph/colors (только tokens из components/astro).

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/synastry-detail.spec.ts
```
E2E-кейсы — §10 wheel-TZ (1-9, 11-14); snapshots — good/bad/selected planet/selected aspect/approximate/320px/390px.

## 9. Expected evidence
- `git diff --name-only` — только файлы из scope.
- Вывод проверок, список snapshot-файлов.

## 10. Escalation rule
Нужны backend правки / миграция существующих карт → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
