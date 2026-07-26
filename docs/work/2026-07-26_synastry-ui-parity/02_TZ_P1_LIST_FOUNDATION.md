# 02_TZ (P1): Синастрия UI parity — основа и список партнёров (Этап 1)

## 1. Packet title
Synastry UI parity, срез P1: tone helper, визуальная основа, hero, карточка партнёра, search/filters, precision/pending states списка.

## 2. Phase / Wave
W-SYNASTRY-MVP, parity wave. Master TZ: `docs/work/2026-07-26_synastry-ui-parity/00_TZ_REACT_PARITY.md` (§3.1, §3.2, §3.7, §4, §5, §16-19 — читать обязательно до начала). Visual reference: `docs/work/2026-07-26_synastry-ui-parity/proto-list.png` (эталон) и `impl-list.png` (текущее состояние), prototype CSS — `docs/work/2026-07-26_synastry-ui-parity/prototype/base.html` + `styles.css`.

## 3. Modules
- Frontend: `components/synastry/*` (list), `app/globals.css` (только additive --syn-*)
- API micro-extension: `apps/api/app/schemas/synastry.py`, `apps/api/app/api/synastry.py` (только list endpoint)

## 4. Goal
Экран `/synastry` визуально соответствует макету (критерии §21 «Список»):
1. `synastry-tone.ts` с `normalizeSynastryTone` (§16) — все цвета/счётчики через него.
2. Визуальная основа §4: тёплый фон с 2 мягкими radial-пятнами (лаванда справа сверху, персик слева в верхней трети) в пределах экрана; tone-палитра `--syn-good/-bg, --syn-mid/-bg, --syn-bad/-bg` (значения §4.1, additive в `app/globals.css`); шрифтовые правила §4.3 (display serif — существующий `font-serif` стек, НЕ менять глобальные шрифты; крупные serif без font-bold).
3. Hero §5.2: eyebrow СИНАСТРИЯ, H1 «Кто тебе подходит?» (38-40px serif, weight 400-500, lh ~1.0), lead-абзац, CTA «＋ Добавить человека» на всю ширину (h 50-54px, radius 16-18px).
4. Search §5.3 (48px, radius 17, placeholder «Найти по имени», мягкий focus) + filters §5.4 (Все/Хорошо подходит/Нормально/Сложно, активный — тёмный ink, scroll без scrollbar). Search фильтрует по имени на клиенте; filters — по нормализованному status.
5. Заголовок списка §5.5 («Твои сравнения» + счётчик).
6. Карточка партнёра §5.6: avatar 46×46 r17, имя 18px, relation по-русски (romantic→«Романтические отношения», friend→«Дружба», business/work→«Работа», family→«Семья»; неизвестное — sentence-case без CSS capitalize), score 29px serif + «/100», status-pill §5.6 (Хорошо подходит/Нормально/Сложно — НЕ «Отличная связь» и т.п.), summary 1-2 строки, три tone-мини-блока счётчиков (из API counters), precision-строка при approximate §5.6, ribbon «ЛУЧШЕЕ СОВПАДЕНИЕ» по правилам §5.7, pending state §5.8 (stage из report_state, copy «Собираем аспекты»/«Готовим человеческий перевод»). Никаких вложенных interactive elements (§5.6: article-контейнер + отдельные кнопки open/delete).
7. API: в `SynastryPartnerItem` добавить `counters: dict | None` и `report_state: str | None`; list endpoint заполняет из det payload (`det.get("counters")`) и `report.state` (None если репорта нет). Обратная совместимость — поля optional.

## 5. Exact write scope
- `components/synastry/synastry-tone.ts` (новый)
- `components/synastry/synastry-list-hero.tsx` (новый)
- `components/synastry/synastry-search-filters.tsx` (новый)
- `components/synastry/synastry-partner-card.tsx` (новый)
- `components/synastry/synastry-screen.tsx` (переСборка из подкомпонентов, сохранить data-testid контракт)
- `app/globals.css` (ТОЛЬКО additive: --syn-* переменные)
- `apps/api/app/schemas/synastry.py` (только SynastryPartnerItem)
- `apps/api/app/api/synastry.py` (только list_synastry_partners)
- `__tests__/synastry/synastry-screen.test.tsx`, `__tests__/synastry/synastry-partner-card.test.tsx` (новый)
- `apps/api/tests/test_synastry_api.py` (кейс counters/report_state в list)
- `e2e/mock-visual/synastry.spec.ts` + snapshots (обновить list-скриншот под новую вёрстку, --update-snapshots)

## 6. Frozen / Out of scope
- Detail screen, wheel, drilldown, add sheet — срезы P2-P4, НЕ трогать.
- Глобальные шрифты/тему, AppShell, TabBar, другие разделы — не трогать.
- Backend pipeline/service/models — не трогать.
- `lib/api/synastry.ts` — только если нужно добавить поля в тип PartnerItem (counters/reportState); больше ничего.

## 7. Must-preserve invariants
- data-testid контракт списка: `synastry-screen` (data-state), `synastry-card` (data-status), add-button — сохранить имена; добавлять новые testid для hero/counters/precision.
- Нет вложенных button (§21); icon-only buttons с aria-label; touch target ≥44px.
- Цвет не единственный носитель смысла (text label у tone-индикаторов).
- Все существующие тесты остаются зелёными (обновление допустимо только в scope-файлах).
- GRACE-разметка в frontend-файлах по канону (AI_HEADER/MODULE_CONTRACT с owned_tests).
- Backend: additive-only, GRACE-разметка, grace_lint PASS.

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_synastry_api.py -q
python3 scripts/grace_lint.py apps/api/app
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/synastry.spec.ts
```

## 9. Expected evidence
- `git diff --name-only` — только файлы из scope.
- Вывод всех проверок (зелёные), обновлённый snapshot списка.

## 10. Escalation rule
Нужен scope P2-P4 / глобальные стили / backend за пределами list endpoint → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
