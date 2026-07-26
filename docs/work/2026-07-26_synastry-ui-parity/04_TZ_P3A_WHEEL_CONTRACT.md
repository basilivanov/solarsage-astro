# 04_TZ (P3a): Синастрия — planet points contract для wheel (backend)

## 1. Packet title
Synastry UI parity, срез P3a: расширение API-контракта отчёта реальными позициями планет (longitude/sign/house) и стабильными planet IDs для SVG-карты. Зависит от P2.

## 2. Phase / Wave
W-SYNASTRY-MVP, parity wave. Master TZ §7.3 + `docs/work/2026-07-26_synastry-ui-parity/01_TZ_INTERACTIVE_SVG_WHEEL.md` §8 (data contract — читать обязательно).

## 3. Modules
- M-SYNASTRY-SERVICE (`apps/api/app/services/synastry_service.py`)
- `apps/api/app/schemas/synastry.py`, `apps/api/app/api/synastry.py` (только report response)
- `lib/api/synastry.ts` (типы)

## 4. Goal
Отчёт `GET /api/synastry/{partner_id}` содержит всё для геометрии карты (01_TZ §8):

1. **Persist в pipeline**: `run_report_pipeline` сохраняет в `deterministic_payload_json` дополнительно `owner_planets` и `partner_planets` из ответа sidecar (поля у sidecar: `name, longitude, latitude, sign, retrograde` — см. `apps/solarsage/solarsage/services/synastry.py:63-97`). Формат точки:
```json
{"id": "owner_sun", "owner": "user", "planet": "Sun", "longitude": 123.45, "sign": "Leo", "retrograde": false, "house": null, "house_reliable": false}
```
   - id = `{owner|partner}_<name.lower()>`; partner-точки — `owner: "partner"`.
   - **house partner-планет**: когда sidecar вернул `partner_houses` (cusps) — вычислить номер дома по cusp longitudes (алгоритм как `_find_house` в `apps/api/app/services/normalization_service.py`), `house_reliable=true`. Approximate/нет houses → `house=null`, `house_reliable=false`. Owner-точкам house всегда null/false (sidecar owner houses не отдаёт).
   - `precision_flags.houses_available` из sidecar учитывать.
2. **Schema**: `SynastryPlanetPoint` (CamelModel, поля как выше); в `SynastryReport` response добавить `owner_planets: list[SynastryPlanetPoint]`, `partner_planets: list[SynastryPlanetPoint]` (default []). В `SynastryAspect` добавить `owner_planet_key: str | None`, `partner_planet_key: str | None` (значения = id точек: `owner_sun`/`partner_moon`), `aspect_symbol: str | None`, `orb_degrees: float | None`, `orb_label: str | None` (формат `1°12′`).
3. **Endpoint маппинг**: `get_synastry_report` заполняет planet points из det payload; aspect keys маппит из det aspect (`owner_planet`/`partner_planet` имена → `{owner|partner}_<lower>`); orb_label форматирует из orb_degrees. Старые репорты без planet данных → пустые списки (не 500).
4. **Frontend types** в `lib/api/synastry.ts`: `SynastryPlanetPoint` + новые optional поля aspect'а (совместимо с CamelModel camelCase).

## 5. Exact write scope
- `apps/api/app/services/synastry_service.py` (persist planet points + house calc)
- `apps/api/app/schemas/synastry.py` (SynastryPlanetPoint, SynastryReport, SynastryAspect поля)
- `apps/api/app/api/synastry.py` (только get_synastry_report маппинг)
- `lib/api/synastry.ts` (типы)
- `apps/api/tests/test_synastry_service.py`, `apps/api/tests/test_synastry_api.py`

## 6. Frozen / Out of scope
- Frontend wheel/компоненты — P3b.
- Sidecar (`apps/solarsage/*`) — не трогать (в ответе всё есть).
- Models/migrations (det payload — JSON Text, миграция не нужна).
- Scoring algorithm.

## 7. Must-preserve invariants
- Никаких выдуманных longitudes; нет данных → пустой список, НЕ fallback-координаты (01_TZ §8 запреты).
- approximate → house_reliable=false всегда.
- Старые payload без planets не ломают response (пустые списки).
- GRACE-разметка; grace_lint PASS; существующие тесты зелёные.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_synastry_service.py tests/test_synastry_api.py -q
python3 scripts/grace_lint.py apps/api/app
```
Тесты: persist planet points (мок sidecar с planets+houses) → house вычислен, approximate → house_reliable=false; endpoint отдаёт points и aspect keys; старый det без planets → пустые списки.

## 9. Expected evidence
- `git diff --name-only` — только файлы из scope.
- Вывод проверок. В отчёте: формат точки и пример orb_label.

## 10. Escalation rule
Нужен sidecar/frontend/models → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
