# 08_TZ (X1): Pixel-perfect — типографика Georgia + экран списка

## 1. Packet title
Synastry pixel-perfect, срез X1: synastry-scoped Georgia для display-элементов + список партнёров 1:1 по макету (computed styles).

## 2. Phase / Wave
W-SYNASTRY-MVP, pixel-perfect wave. Эталон (читать CSS оттуда, не проектировать самому):
- `docs/work/2026-07-26_synastry-ui-parity/prototype/base.html` — inline `<style>` + разметка экранов
- `docs/work/2026-07-26_synastry-ui-parity/proto-list.png` — визуальный эталон списка
- Колесо (SVG) — ВНЕ scope: наша версия с зодиаком остаётся (решение владельца).

## 3. Modules
- `components/synastry/synastry-list-hero.tsx`, `synastry-search-filters.tsx`, `synastry-partner-card.tsx`, `synastry-screen.tsx`
- `app/globals.css` (additive: `.syn-serif` scope)

## 4. Goal

### 4.1. Georgia scope
В `app/globals.css` additive: `.syn-serif { font-family: Georgia, "Times New Roman", serif; }`. Применить ко ВСЕМ display serif элементам синастрии (h1 списка, «Ты + Имя», score-числа 29px+, sphere scores, заголовок «Добавить человека» в sheet). Глобальный font-serif стек (Instrument/Lora) НЕ менять, другие разделы не трогать. Интерфейсный текст — Inter (как сейчас).

### 4.2. Brand topbar (есть в макете, нет у нас)
Над hero: topbar h58px: слева brand «✦ SOLAR SAGE» (mark 25px круг plum + текст 12px/800 uppercase ls .13em), справа icon-btn 40px radius 15px «i» (aria-label «О синастрии», onClick — toast/alert не нужен, пока disabled без заглушки-тоста, просто нет action). Эталон: base.html `.topbar`, `.brand`, `.brand-mark`, `.icon-btn`.

### 4.3. Hero (computed diff — выровнять)
| Элемент | Свойство | Макет | Сейчас |
|---|---|---|---|
| h1 | font | Georgia 40px/500, ls -1.4px(-0.035em), lh .98 | 38px/400 |
| lead | font | Inter 15px, lh 1.55, color var(--muted) | 14px |
| CTA | font | Inter 16px/760, padding 15px 18px, radius 17px, БЕЗ shadow | 15px/600 h-52 shadow-sm |
Copy h1/lead/CTA — как сейчас (тексты совпадают).

### 4.4. Search & filters
- search: height 48px, radius 17px, font 16px, padding `0 44px`, bg rgba(255,255,255,.82), border var(--line) #e8e0e8, focus: border rgba(121,90,134,.5) + shadow 0 0 0 4px rgba(121,90,134,.08).
- filter chips: padding 9px 12px, radius 999px, font 12px/730, inactive bg rgba(255,255,255,.72) border var(--line); active bg var(--ink) #3e3347 color #fff. Эталон: base.html `.filters`, `.filter`.

### 4.5. Section head
«Твои сравнения» — Inter 20px/700 (НЕ serif); справа счётчик «N из M» 12px var(--muted). Эталон: `.section-head`.

### 4.6. Карточка партнёра (1:1 по `.candidate` и детям)
- card: border `1px solid rgba(121,90,134,.13)`, bg `rgba(255,253,249,.94)`, radius 24px, padding 16px, shadow `0 8px 26px rgba(73,51,82,.055)` (убрать shadow-sm).
- ribbon `.best-ribbon`: absolute right 14px top -8px, bg var(--plum) #795a86, color #fff, radius 999, padding 5px 9px, font 9px/850 uppercase ls .08em, текст «ЛУЧШИЙ ОБЩИЙ БАЛАНС». Правила показа — как сейчас (max score среди ready, >1 карточки).
- top row: `.candidate-top` flex gap 12px; avatar `.cand-ava` 46×46 radius 17px bg var(--lav) #f1e9f4 color var(--plum), initial Georgia 18px; имя `.candidate-name` Inter 18px/800 (НЕ serif); meta `.candidate-meta` 12px var(--muted).
- score `.score`: Georgia 29px/400 lh 1 ink, НИЖЕ `small` «из 100» Inter 10px/700 muted block. Убрать inline «/100».
- status `.status`: inline-flex gap 6px, radius 999, padding 6px 9px, font 11px/800, с tone-dot «●» перед текстом, цвета fg/bg из --syn-* (good/mid/bad). Label: «Хорошо подходит/Нормально/Сложно» (как сейчас).
- summary `.candidate-copy`: 14px lh 1.42, БЕЗ line-clamp.
- counters `.balance`: grid 3 колонки gap 7px, tile radius 14px padding 10px 7px center: number `<strong>` 18px/760 block, label 10px/760 — т.е. «8» крупно + «поддерживают» мелко (не одной строкой 11.5px). Цвета --syn-*.
- precision-строка: оставить (наш функциональный плюс, стиль 11.5px muted).
- delete: оставить как есть (отдельная кнопка, в макете нет — наш плюс).
- pending state: оставить (наш плюс), score-позиция — loader как сейчас.

### 4.7. Фон экрана
Макет: 2 radial-пятна (лавандовое `circle at 82% -4%` rgba(188,155,198,.28) transparent 28%; персиковое `circle at -10% 16%` rgba(245,217,208,.38) transparent 24%) поверх #fbf8f2 — реализовать внутри `data-testid="synastry-screen"` контейнера (CSS на корне экрана, НЕ на AppShell глобально).

## 5. Exact write scope
- `app/globals.css` (additive .syn-serif)
- `components/synastry/synastry-list-hero.tsx` (+topbar)
- `components/synastry/synastry-search-filters.tsx`
- `components/synastry/synastry-partner-card.tsx`
- `components/synastry/synastry-screen.tsx` (фон, section head)
- `__tests__/synastry/synastry-screen.test.tsx`, `__tests__/synastry/synastry-partner-card.test.tsx`
- `e2e/mock-visual/synastry.spec.ts` + snapshots (обновить)

## 6. Frozen / Out of scope
- SVG wheel (наша версия), detail screen, add sheet, drilldown — срез X2.
- Глобальные шрифты/тема, AppShell, TabBar, backend.
- Тексты менять нельзя (copy уже согласованы), только стили/структура.

## 7. Must-preserve invariants
- data-testid контракт: `synastry-screen`(data-state), `synastry-card`(data-status), `synastry-add-btn`, `synastry-card-counters`, `synastry-precision-note`, `synastry-list-hero`, новый `synastry-brand-topbar`.
- Нет вложенных interactive; aria-label у icon buttons; ≥44px touch targets (icon-btn 40px в макете — у нас оставить 44px, визуально близко).
- --syn-* токены для tone (не хардкод hex).
- Все существующие тесты зелёные (snapshots обновить).

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/synastry.spec.ts
node docs/work/2026-07-26_synastry-ui-parity/pixel-diff.cjs   # computed-style diff, цель: 0 расхождений по LIST-точкам
```

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок + вывод pixel-diff (чистый по LIST).

## 10. Escalation rule
Нужен detail/add/drilldown/global scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
