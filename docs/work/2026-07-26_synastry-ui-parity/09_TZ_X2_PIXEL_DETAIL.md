# 09_TZ (X2): Pixel-perfect — detail, форма добавления, drill-down, модалки/триггеры

## 1. Packet title
Synastry pixel-perfect, срез X2: детальный экран, add sheet, drill-down sheet, модальные взаимодействия (combined tech, тосты) — 1:1 по макету. Зависит от X1 (Georgia scope, токены).

## 2. Phase / Wave
W-SYNASTRY-MVP, pixel-perfect wave. Эталон CSS (копировать значения, не проектировать):
- `docs/work/2026-07-26_synastry-ui-parity/prototype/base.html` (inline `<style>`, `.score-panel`, `.overlay`, `.translation`, `.sphere`, `.aspect`, `.feedback`, `.modal`, `.toast`, `.sheet`, `.field`, `.input`, `.input-row`)
- `prototype/detail.css` (`.pair-hero`, `.pair-avatars`, `.pair-title`, `.pair-sub`)
- `prototype/aspect-drilldown.css` (`.aspect-modal-*`, `.planet-*`, `.meaning-*`, `.life-*`, `.repair-*`, `.not-means`)
- `prototype/partner-time.css` (switch + precision note)
- Скриншоты-эталоны: `proto-detail.png`, `proto-add.png`, `proto-drilldown.png`
- SVG wheel — НЕ трогать (решение владельца: наша версия с зодиаком лучше макета).

## 3. Modules
- `components/synastry/synastry-pair-hero.tsx`, `synastry-score-panel.tsx`, `synastry-aspect-row.tsx`, `synastry-house-overlays.tsx`, `synastry-translations.tsx`, `synastry-spheres.tsx`, `synastry-feedback.tsx`, `synastry-detail-screen.tsx`, `synastry-add-sheet.tsx`, `aspect-drilldown-sheet.tsx`
- Backend: `apps/api/app/services/synastry_service.py` (только `_match_translation_aspect_id`)

## 4. Goal

### 4.1. Detail hero (`detail.css`)
- avatars: 74×74, radius 25px, font Georgia 29px, `box-shadow: 0 8px 22px rgba(61,49,74,.1), 0 0 0 5px var(--bg)`; первый `translateX(-27px) rotate(-4deg)`, второй `translateX(27px) rotate(4deg)`; контейнер h80px.
- pair-title: Georgia 33-34px, lh 1.03; pair-sub/meta: 13px muted (у нас 12.5 — ок, выровнять 13px).

### 4.2. Score panel (`base.html .score-panel`)
- card: radius 26px, padding 18px, border var(--line), shadow var(--shadow) (`0 8px 26px rgba(73,51,82,.055)`).
- score-line: tile 78×78 (уже есть) + h2 21px + p 13px muted lh 1.45.

### 4.3. Aspect rows (`base.html .aspect*`)
- row: border var(--line), radius 16px, padding 11px, bg #fff; active: border rgba(121,90,134,.45) + shadow `0 0 0 3px rgba(121,90,134,.07)`.
- symbol square: 27×27 radius 10px, font 15px/850, tone цвета --syn-*.
- title `.aspect-tech`: Inter 13px/830 (НЕ serif); orb справа (как есть); human `.aspect-human`: 12px lh 1.4 muted, padding-left 35px; hint «Нажми — подробное значение и примеры» (БЕЗ стрелки →).
- «Показать все аспекты ↓»: текстовая кнопка plum по центру (не bordered full-width); раскрытие — «Скрыть второстепенные аспекты ↑».
- Wheel card sub (verbatim из макета): «Два кольца — ваши планеты. Зелёные линии поддерживают, жёлтые раскачивают, красные дают трение. Нажми на линию или контакт ниже.»

### 4.4. Overlays (`.overlay`)
- bg #f7f2f7, radius 17px, padding 12px; tech 11px/850 plum; text 12px lh 1.42, margin 0. Без border.

### 4.5. Translations (`.translation*`)
- card: radius 18px, padding 14px, bg #fff, border var(--line).
- top: tone-dot + h3 Inter 15px; справа techline: font 10px muted, dotted underline, формат «{tech} · что значит?».
- text: 13px lh 1.46; scene: bg #f8f5f8, radius 12px, padding 9px 10px, color #65596a, font 12px (НЕ italic).

### 4.6. Spheres (`.sphere*`)
- row: radius 18px border var(--line) bg #fff; summary padding 14px, font 14px/820; score Georgia 22px/500 справа; content 13px lh 1.48 #5e5262.

### 4.7. Feedback (`.feedback`)
- grid 3 колонки gap 7px; button: border var(--line), bg white, radius 14px, padding 10px 6px, font 11px/760; active: bg var(--ink), color #fff, border-color var(--ink).

### 4.8. Add sheet
- overlay `.modal`: `rgba(44,35,48,.35)` БЕЗ backdrop-blur.
- sheet `.sheet`: bg var(--bg), radius 28px top, padding 20px 18px max(22px, safe-area), H2 Georgia 24px.
- labels `.field label`: 11px/800, ОБЫЧНЫЙ регистр («Имя», «Место рождения»), margin-bottom 6px.
- inputs `.input`: h46px, radius 14px, border var(--line), padding 0 13px.
- «Дата и время рождения» — ОДНО поле-метка, date+time в `.input-row` (grid 1.2fr/.8fr, gap 8px).
- switch-row (partner-time.css): заголовок «Точное время неизвестно» + подзаголовок «Можно построить синастрию и без него»; precision-линия ВСЕГДА видна: exact → зелёная «Точный расчёт: аспекты, ASC и наложение домов», unknown → янтарная «Примерный расчёт…» (текст как сейчас).
- CTA «Построить синастрию»: `.primary.full` — radius 17px, padding 15px 18px, Inter 16px/760.

### 4.9. Drill-down sheet (`aspect-drilldown.css`)
- hero `.aspect-modal-hero`: gradient `135deg,#f6eef8,#fff8f1`, radius 20px, padding 14px, gap 13px; symbol 50×50 radius 17px font 27px/850 tone-цвета; h2 22px Georgia (headline); meta 11px muted («Квадрат · орб 1°05′ · напряжённый контакт»).
- section titles `.meaning-section-title`: 11px/850 ls .09em uppercase plum.
- planet cards `.planet-meaning`: bg #f7f2f7 / partner #fbf3ed, radius 17px, padding 13px; owner-label 9px/850 uppercase muted; strong 14px; p 11.5px lh 1.42 #65596a.
- meaning cards `.meaning-card`: border var(--line), radius 17px, padding 13px; h3 14px; p 12.5px lh 1.5 #5e5262.
- scenes `.life-scene`: bg #f8f5f8, radius 16px, padding 12px; b 12px block; span 12px lh 1.45 #65596a.
- repairs `.repair-item`: border #dce9e3, bg #f4faf7, radius 15px, padding 10px, grid 25px+1fr; num square 25px radius 9px good-bg/good 11px/850; p 12px #52645d.
- not-means `.not-means span`: radius 999px, bg #f3eff4, color #695d6d, font 10px/760, padding 7px 9px.

### 4.10. Модальные взаимодействия
- Backend `_match_translation_aspect_id`: матчить ПЕРВЫЙ аспект, чья нормализованная подпись (planets+type БЕЗ индекса) содержится в нормализованном tech — как `openAspectFromTech` в макете. Combined tech «Марс ☍ Марс + Меркурий □ Меркурий» → первый аспект (Марс☍Марс). Нормализация id: «mars_opposition_mars_2» → «marsoppositionmars» (отрезать _\d+$). Тест на combined tech.
- Тосты (через существующий `hooks/use-toast.ts`): feedback success → «Сохранили: {label}»; share icon (в detail topbar, сейчас disabled) → «Расшаривание заложено, но пока выключено»; info «i» (brand topbar из X1) → «Синастрия: карта того, как две натальные карты взаимодействуют между собой». Стиль тоста приблизить к макету (bottom, тёмный bg #3f3445, radius 14px) настолько, насколько позволяет use-toast без его переработки.

## 5. Exact write scope
- Перечисленные 10 tsx-компонентов synastry
- `apps/api/app/services/synastry_service.py` (только `_match_translation_aspect_id`)
- `apps/api/tests/test_synastry_service.py` (combined tech кейс)
- `__tests__/synastry/*.tsx` (обновить/добавить)
- `e2e/mock-visual/synastry-detail.spec.ts` + snapshots

## 6. Frozen / Out of scope
- SVG wheel (наша версия), список (X1), backend кроме matcher'а, TabBar/AppShell/globals (кроме ничего).
- Тексты макета копировать верbatim; не менять copy, уже совпадающий.

## 7. Must-preserve invariants
- data-testid контракт всех экранов (из P1-P3): `synastry-detail-screen`, `synastry-hero`, `synastry-score`, `synastry-wheel`, `synastry-aspect`, `synastry-add-sheet`, aria-атрибуты.
- --syn-* токены для tone; `.syn-serif` (X1) для Georgia-элементов.
- Старые payload без aspectId — кнопка скрыта (уже есть).
- Все существующие тесты зелёные; grace_lint PASS.

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_synastry_service.py -q
python3 scripts/grace_lint.py apps/api/app
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/synastry-detail.spec.ts
```

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок; combined-tech кейс в pytest.

## 10. Escalation rule
Нужен list/wheel/global scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
