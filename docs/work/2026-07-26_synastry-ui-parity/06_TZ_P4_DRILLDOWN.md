# 06_TZ (P4): Синастрия — drill-down аспекта: новый контракт + sheet (Этап 4)

## 1. Packet title
Synastry UI parity, срез P4: структурный drill-down (planet cards, scenes[], repairs[], notMeans[]) и переработанный bottom sheet. Зависит от P2/P3.

## 2. Phase / Wave
W-SYNASTRY-MVP, parity wave. Master TZ §3.5, §12 (читать обязательно целиком), §16-19. Reference: `proto-drilldown.png` / `impl-drilldown.png`, prototype — `prototype/aspect-drilldown.css`, `aspect-drilldown.js`.

## 3. Modules
- Backend: M-SYNASTRY-SERVICE (drilldown mapping), M-LLM-SYNASTRY (meanings), schemas
- Frontend: `components/synastry/aspect-drilldown-sheet.tsx`

## 4. Goal

### Backend — контракт §12.8
`GET /api/synastry/{partner_id}/aspect/{aspect_id}` отдаёт структурный `AspectDrilldown`:
1. LLM уже генерирует `intro/scenes/repairs/not_means` (build_drilldown_prompt) — СЕЙЧАС они склеиваются в flat scenario/advice. Сохранять в `SynastryAspectDetail.payload_json` СТРУКТУРНО: `explanation` (intro), `scenes: [{title,text}]` (3-5), `repairs: [str]` (3-5), `not_means: [str]` (ровно 3, validate_drilldown_output уже проверяет).
2. Schema `AspectDrilldown` расширить по §12.8: `aspect_symbol`, `aspect_kind_label` (Квадрат/Тригон/Секстиль/Соединение/Оппозиция/Квиконс), `orb_text` («орб 1°05′»), `headline` (human title), `owner_planet`/`partner_planet`: {key, label, glyph, meaning} — meaning из `PLANET_MEANINGS` (`synastry_llm.py`, для разных планет разные тексты); `explanation`, `scenes`, `repairs`, `not_means`. Старые `scenario`/`advice` оставить optional как fallback.
3. Символ аспекта и kind label — из aspect_type det-аспекта (маппинг §8.2 master). Planet glyph — статическая таблица (☉☽☿♀♂♃♄ и т.д.).
4. Механика аспекта («Как работает квадрат») — из `ASPECT_MEANINGS` (`synastry_llm.py`), поле в payload: `aspect_mechanics: str`.
5. Aspect не найден → 404 (уже есть). LLM failure → failed detail, base report untouched (уже есть, сохранить).
6. Старые детали в БД (flat payload) — backward compat: schema отдаёт scenario/advice, новых полей нет → frontend fallback.

### Frontend — sheet §12.1-12.7
7. Формат §12.1: bottom sheet, max-height 90dvh, rounded top 28, grabber, внутренний scroll, bg = app background, close icon, CTA «Понятно».
8. Hero §12.3: eyebrow «АСТРОЛОГИЧЕСКИЙ КОНТАКТ», тех-сигнатура заголовком («Меркурий □ Меркурий»), tone-квадрат с символом 50px + headline + meta (`{kind} · {orb} · {тон контакта}`).
9. Две planet cards §12.4 (ТВОЯ КАРТА — лаванда / КАРТА ПАРТНЁРА · {имя} — персик): glyph + название + meaning.
10. Механика аспекта §12.2(3) — отдельная секция.
11. Сцены §12.5: массив named cards (title+text); fallback: один старый scenario.
12. Repairs §12.6: нумерованные зелёные карточки; fallback: старый advice.
13. Not means §12.7: chips «Важно: это не означает»; fallback: 3 нейтральных по tone.
14. Никакого хардкода «не означает» одинакового для всех (текущий баг aspect-drilldown-sheet.tsx:154-173).

## 5. Exact write scope
- `apps/api/app/services/synastry_service.py` (только get_aspect_drilldown + helpers)
- `apps/api/app/services/synastry_llm.py` (meanings dicts при необходимости)
- `apps/api/app/schemas/synastry.py` (AspectDrilldown)
- `components/synastry/aspect-drilldown-sheet.tsx`
- `lib/api/synastry.ts` (тип AspectDrilldownData)
- `apps/api/tests/test_synastry_service.py` (структурные кейсы)
- `__tests__/synastry/aspect-drilldown-sheet.test.tsx` (новый)

## 6. Frozen / Out of scope
- Wheel (P3), detail screen (P2), list (P1), add sheet (P5).
- Prompt`ы кардинально не менять (build_drilldown_prompt уже просит нужные поля).
- Models/migrations.

## 7. Must-preserve invariants
- LLM failure → только detail failed (инвариант master 10.2), base report READY.
- Backward compat со старыми flat payloads (Вася и др. не ломаются).
- validate_drilldown_output не ослаблять (not_means ровно 3, scenes 3-5).
- a11y: Escape/overlay-close, focus return, aria.
- GRACE-разметка; grace_lint PASS; существующие тесты зелёные.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_synastry_service.py -q
npx vitest run __tests__/synastry
python3 scripts/grace_lint.py apps/api/app
```

## 9. Expected evidence
- `git diff --name-only` — только файлы из scope.
- Вывод проверок. В отчёте: пример структурного payload для квадрата Меркуриев.

## 10. Escalation rule
Нужен wheel/list/models/prompt-переработка → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
