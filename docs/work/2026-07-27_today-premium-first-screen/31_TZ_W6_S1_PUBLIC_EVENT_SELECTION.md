# 31 TZ W6-S1 — Public Event Selection (B2.1) — backend slice

1. **Packet title**: W6-S1-PUBLIC-EVENT-SELECTION
2. **Phase / Wave**: W6-FOCUS-HARDENING, срез S1 (backend). Normative source:
   `27_TZ_W4_AMENDMENT_PUBLIC_EVENT_SELECTION.md` (далее «amendment») — обязателен
   к прочтению целиком; реализуется §3 (selection), §3.4 (display order),
   §4 (canary oracle), §6.1/§6.2/§6.3 (scope/audit/version).
3. **Modules**: M-TODAY-FOCUS-BUILDER, M-FOCUS-TITLE-BUILDER (только eligibility),
   M-DAY-SERVICE.audit (scripts/audit_day_contract.py), M-CORE-VERSIONS.
4. **Goal**: `build_today_focus` выбирает public events по нормативному канону
   amendment §3, а не по рангу convergence-группы. На sanitized canary 28.07
   (Europe/Moscow) selected set = `ev:act:t2n__MOON__SQUARE__PLUTO` (13:31),
   `ev:act:t2n__MOON__SEXTILE__URANUS` (18:19), `ev:act:t2n__MARS__OPPOSITION__NEPTUNE`
   (19:52) — в display order по occurs_at.

## Entry gate (проверено ревьюером, фиксирую здесь)

- C2 принят clean commits (99a25c0a, 3fb6fd32) — prompt/contentState/titles в main.
- Title builder не возвращает machine-key fallback для известных типов
  (Плутон/жребий/дома проверены live).
- `TodayFactor` несёт `aspect_type`/`target_type`/`house`.
- Reducer-вопрос (case J) НЕ блокирует этот срез: grouping и ranking победителя
  frozen (§7 amendment), селектор работает ПОСЛЕ выбора победителя и не «чинит»
  reducer. Case J остаётся blocked-decision в W6-S2.

## 5. Exact write scope

- `apps/api/app/services/today_focus_builder.py` — отделить public event
  selection от group ranking; pure block `PUBLIC_EVENT_SELECTION`.
- `apps/api/app/services/focus_title_builder.py` — ТОЛЬКО добавить
  `check_public_title_eligibility(human_title) -> str | None` (reason code или
  None). Существующие словари не дублировать.
- `apps/api/tests/test_today_focus_builder.py` — новые тесты §8.1 amendment.
- `apps/api/app/core/versions.py` — `TODAY_CONTENT_VERSION` 11 → 12 (одна строка,
  комментарий «W6-S1 public event selection»).
- `scripts/audit_day_contract.py` — sanitized focus-секция в выводе (§6.2
  amendment): state, contentState, convergence theme/count, selected events
  (local time, id, kind), инварианты cap/date/source IDs. Никаких raw
  profile/birth/TG/LLM evidence в выводе.

## 6. Frozen / Out of scope

- Grouping и ranking победившей convergence-группы, valence reducer, dayStatus,
  relativeStatus, featured-sphere ranking — НЕ трогать.
- `today_service.py`, `llm_service.py`, `day_pregen.py`, cache/pregen —
  это W6-S4 (O1), здесь ЗАПРЕЩЕНЫ (amendment §6.3: нельзя менять provider
  chain и селектор одним diff).
- Wire schema / OpenAPI / contracts regen — не меняется (selection semantics
  не добавляет полей).
- Frontend — W6-S3.
- Удаление legacy полей — запрещено.

## 7. Must-preserve invariants

- Все существующие тесты зелёные (разрешено осознанно обновить ожидания
  `test_today_focus_builder.py`, если они фиксировали СТАРЫЙ group-order
  selection — каждое такое изменение перечислить в отчёте с обоснованием).
- `state`, `convergence`, `featured_spheres`, `background_factors` семантика
  не меняется (background_factors строятся из winning group как раньше).
- Детерминизм: одинаковый canonical input → одинаковый selected set независимо
  от permutation и wall-clock (amendment §3.3: strength — canonical snapshot).
- `python3 scripts/grace_lint.py app` → PASS; ruff/mypy чисто.

## Нормативный дизайн (обязателен)

Реализовать в `today_focus_builder.py` как отдельный pure блок после ranking
групп (amendment §3):

1. **Candidate pool** (§3.1): факторы `temporal_role="anchor_today"` с kind
   `exact|starts|peak|building|separating`; exact/starts/peak — строго внутри
   локального дня; provenance (`activation_ids` или factor id); title
   eligibility; без physical/semantic дублей (по factor_id).
2. **Title eligibility** (§3.1 п.5, §3.1.1): `check_public_title_eligibility`
   возвращает reason (`machine_key`, `empty_title` …) или None. Machine key =
   `Transit_`/`Natal_`/`transit_`/`natal_` или токен `[A-Z][A-Z0-9_]{2,}`
   (3+ заглавных/цифр/underscore: NECESSITY, ANGULAR_PLANET, SESQUI_QUADRATE).
   Проверяется human_title. Неeligible → кандидат пропускается, селектор берёт
   следующего (§8.1.6/§8.1.17 — reason code доступен для теста/лога).
3. **Reserved winner anchor** (§3.2): одно место под primary anchor победившей
   группы; если он не eligible — следующий eligible anchor той же группы по
   детерминированному порядку; если ни одного — событие не публикуется, кейс
   помечается contract anomaly (тест), state НЕ переписывается.
4. **Remaining slots** (§3.3): остальные anchors всех групп + незагруппированные
   ранжируются: (1) precision: exact_today > starts_today > delta_peak;
   (2) valenced (supportive|tense|mixed) > neutral; (3) strength desc;
   (4) occurs_at asc, nulls last; (5) factor_id asc. Cap общий = 3.
   Запрещены: re-rank по позиции группы, forced positive balancing, LLM score.
5. **Display order** (§3.4) после выбора: `(occurs_at is null) ASC,
   occurs_at ASC, id ASC`. null-time событие — без выдуманных часов, после
   timed (§8.1.15).
6. **States** (§3.6): single_impulses — тот же pool без reserved slot;
   background_only/no_accent — `events=[]`.
7. Event kind/occurs_at/precision для выбранных — как в текущем коде
   (exact→"exact", active_from today→"starts", phase building/separating,
   anchor fallback "peak"). `id = ev:<factor_id>`, provenance
   `source_activation_ids` из factor (§3.1.1 — wire-формат не менять).

Canary test data (§4 amendment) — inline sanitized synthetic factors в тесте
(без profile/birth/TG): Pluto convergence (Moon-Pluto anchor + Mars-Pluto и
др. members), независимые anchors Mars-Opp-Neptune (strength 0.9076,
exact 16:52Z) и Moon-Sextile-Uranus (0.2005, exact 15:19Z), вытесненные
Moon-Quincunx-Necessity (neutral 0.1144) и Moon-Sextile-Mercury (0.0137) —
ожидание ровно из §4 amendment.

## 8. Verification

```bash
cd apps/api && source .venv/bin/activate && \
python -m pytest tests/test_today_focus_builder.py -q && \
python -m pytest tests/ -q -k "not postgres and not election_quota_persists" && \
ruff check app/ && mypy app/services/ && python3 ../../scripts/grace_lint.py app
```

## 9. Expected evidence

- Diff, вывод verification, список осознанно изменённых старых ожиданий,
  canary test output (3 IDs + времена), пример sanitized audit-секции,
  подтверждение что grouping/ranking/today_service не тронуты (git diff --stat).

## 10. Escalation

Понадобилось менять grouping/reducer/today_service/wire schema/LLM —
стоп, доклад ревьюеру (это отдельные packets S4/owner decision).

## 11. No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
