# W4-C1 TZ: TodayFocus схема + детерминированная интеграция в day payload

Дата: 2026-07-28
Phase / Wave: **W4-TODAY-CONVERGENCE**, срез C1 (backend contract)
Родитель: `docs/work/2026-07-27_today-premium-first-screen/21_TZ_W4_TODAY_CONVERGENCE_EVENTS_PERFORMANCE.md` (§5, §12.2)
База: `today_focus_builder.py` (B1/B2 + matching fix, в main)
Modules: новый `M-SCHEMAS-TODAY-FOCUS`, `M-TODAY-SERVICE`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal

`TodayPayload` получает поле `focus` (TodayFocus, §5 родителя), заполненное
детерминированно из B1/B2: state, convergence, events (0–3), featured_spheres
(0–3), `content_state="not_needed"` (LLM-слой — C2). Контракты регенерированы,
frontend может читать блок.

## 2. Exact write scope

- `apps/api/app/schemas/today_focus.py` — **новый** `M-SCHEMAS-TODAY-FOCUS`:
  `TodayFocusEvent`, `TodayFeaturedSphere`, `TodayConvergence`, `TodayFocus`
  (точно по §5: kinds, precision, состояния, content_state enum).
- `apps/api/app/schemas/today.py` — `TodayPayload.focus: TodayFocus | None`.
- `apps/api/app/services/today_service.py` — в build path: после valence/
  horizon — `build_today_focus(...)` из B2 с реальными входами (ledger,
  activation layer, day delta, valence assessments, profile tz); маппинг в
  public схемы; `content_state="not_needed"`. Детерминированный, дешёвый
  (без дополнительных sidecar-вызовов).
- `npm run contracts:generate` + `lib/contracts/today.ts` — регенерация.
- `apps/api/tests/` — contract тесты §12.2: схемы валидны; state !=
  convergence_today → convergence is None и featured == []; events
  отсортированы по occurs_at+id; occurs_at с tz; source ids ссылаются на
  активации; кеш hit/miss дают одинаковый focus.

## 3. Frozen / out-of-scope

- LLM core (C2), frontend (W4-F), sidecar.
- Cache version bump — НЕ делать (focus добавляется аддитивно в payload;
  bump отдельным решением ревьюера после C2).

## 4. Must-preserve

- Все существующие поля payload и их версии не меняются.
- Инварианты §5 родителя (сортировки, caps, tz, provenance ids).
- GRACE + owned_tests.

## 5. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "today_focus"
npm run contracts:check
```

## 6. Expected evidence

- Файлы, вывод verification + contracts:check, пример focus JSON из живого
  дня (текстом).

## 7. Escalation rule

Нужен файл вне §2 — стоп, доложить. Ничего не коммить и не пушить.
