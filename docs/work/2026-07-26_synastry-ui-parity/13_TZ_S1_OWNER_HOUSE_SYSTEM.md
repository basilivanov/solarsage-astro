# S1_TZ: синастрия — единая система домов владельца + детерминированные оверлеи

## 1. Packet title
Synastry house system: обе карты считаются в системе владельца отчёта (auto per-latitude fallback), sidecar возвращает дома обеих карт и resolved house_system, оверлеи — детерминированные из реальных данных.

## 2. Phase / Wave
W-SYNASTRY-MVP, houses correctness. Контекст решения владельца: «синастрия считается в системе пользователя аккаунта»; safety-fallback на |lat|≥60° остаётся per-chart (Плацидус невозможен → Whole Sign).

## 3. Modules
- `apps/solarsage/solarsage/services/synastry.py`, `apps/solarsage/solarsage/schemas/synastry.py`
- `apps/api/app/services/synastry_service.py` (pipeline), `apps/api/app/services/synastry_llm.py` (prompt), `apps/api/app/api/synastry.py` (response), `apps/api/app/schemas/synastry.py`
- `lib/api/synastry.ts` (поле), `components/synastry/synastry-detail-screen.tsx` или `synastry-house-overlays.tsx` (метка системы)

## 4. Goal

### 4.1. Sidecar
- `SynastryRequest`: добавить `house_system: str | None = None` ("PLACIDUS" | "WHOLE_SIGN").
- `calculate_synastry`: обе карты считать в `house_system` (если задан); per-chart safety fallback (≥60° → Whole Sign) сохраняется как нижняя граница. Отследить resolved-систему КАЖДОЙ карты.
- `SynastryResponse`: добавить `owner_houses: list[dict] | None`, `owner_house_system: str`, `partner_house_system: str`.

### 4.2. API pipeline
- Определить систему владельца: по широте профиля (та же ≥60° логика; позже — profile preference, out of scope сейчас) и передать в sidecar.
- **Детерминированные оверлеи** в det payload: для каждой планеты партнёра — дом владельца (`find_house` по owner_houses), для каждой планеты владельца — дом партнёра (partner_houses); формат: `{tech: "Его Венера → твой 7 дом", planet, planet_owner, house, house_system}`. Approximate (нет времени партнёра) — partner overlays пропускаем, owner overlays считаем (владелец точен).
- Persist `house_system` (owner) в det payload.
- Prompt (`build_report_prompt`): передать вычисленные оверлеи фактурой; LLM пишет human-текст СТРОГО по ним (не выдумывать дома); если оверлеев нет (approximate) — дома не упоминать.

### 4.3. Response + UI
- Endpoint: `house_overlays` теперь из det (tech + text из LLM, matched по tech если есть; иначе только tech + template-текст без LLM); поле `house_system` в ответе (owner система, "whole_sign"|"placidus").
- UI: в секции «Наложение домов» маленькая метка системы: «Дома: равнодомная система» / «Дома: Placidus» (по `house_system` ответа). Если данных нет (approximate) — текущая честная карточка остаётся.

## 5. Exact write scope
- `apps/solarsage/solarsage/services/synastry.py`
- `apps/solarsage/solarsage/schemas/synastry.py`
- `apps/solarsage/tests/test_synastry.py`
- `apps/api/app/services/synastry_service.py`
- `apps/api/app/services/synastry_llm.py`
- `apps/api/app/api/synastry.py`
- `apps/api/app/schemas/synastry.py`
- `apps/api/tests/test_synastry_service.py`, `apps/api/tests/test_synastry_api.py`
- `lib/api/synastry.ts`
- `components/synastry/synastry-house-overlays.tsx`

## 6. Frozen / Out of scope
- Profile setting выбора системы (отдельный будущий срез), натал (уже house-aware), wheel-геометрия, scoring.
- Тексты макета не менять.

## 7. Must-preserve invariants
- Safety fallback ≥60° per-chart всегда побеждает (никогда Плацидус на заполярье).
- Кросс-аспекты не меняются (долготы не зависят от домов).
- Approximate: партнёрские дома не выдумываются (уже есть инвариант).
- GRACE-разметка; grace_lint PASS; все существующие тесты зелёные.

## 8. Verification commands
```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_synastry.py -q
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_synastry_service.py tests/test_synastry_api.py -q
python3 scripts/grace_lint.py apps/api/app
```
Кейсы: обе карты в whole_sign при owner lat≥60; owner_houses возвращаются; оверлей детерминирован (известная долгота → известный дом); approximate → партнёрских оверлеев нет; метка системы в ответе.

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок; пример ответа /v1/synastry с owner_houses и house_system.

## 10. Escalation rule
Нужен profile setting / natal scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
