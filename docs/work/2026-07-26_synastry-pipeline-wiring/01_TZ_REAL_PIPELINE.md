# 01_TZ: Синастрия — реальный pipeline в SynastryService (срез A)

## 1. Packet title
Синастрия — реальный run_report_pipeline: sidecar → scoring → LLM → persist (+ refund при failed). Срез A из 4.

## 2. Phase / Wave
W-SYNASTRY-MVP, fix-wave: pipeline wiring.

## 3. Modules
- M-SYNASTRY-SERVICE (`apps/api/app/services/synastry_service.py`)

## 4. Goal
`SynastryService.run_report_pipeline(report_id)` выполняет НАСТОЯЩИЙ расчёт вместо заглушки:
1. PENDING → CALCULATING: читает report + partner + owner UserProfile, вызывает sidecar, маппит cross-aspects в scoring, сохраняет `deterministic_payload_json` и коммитит ДО LLM-фазы.
2. CALCULATING → NARRATIVE_GENERATING: строит prompt через `build_report_prompt`, вызывает LLM, валидирует через `validate_llm_output`, сохраняет `narrative_payload_json` → READY.
3. Любая окончательная ошибка (sidecar недоступен/4xx, LLM 2 неудачные попытки, validation failed) → state=`failed` с осмысленным `error_code` + REFUND: `credit.used_amount -= 1` и `spend.refunded_at = now` в той же транзакции, что и финальный state.

Успех = unit-тесты на pipeline с моками sidecar/LLM зелёные; stub-данные (sample_aspects, hardcoded narrative) полностью удалены.

## 5. Exact write scope
- `apps/api/app/services/synastry_service.py`
- `apps/api/tests/test_synastry_service.py`

## 6. Frozen / Out of scope
- НЕ трогать `app/api/synastry.py` (триггер — срез 02).
- НЕ трогать models, schemas, `synastry_llm.py`, `synastry_scoring.py`, sidecar, frontend.
- НЕ добавлять lease/reconcile job (срез 03) и drilldown LLM (срез 04): `get_aspect_drilldown` оставить как есть.
- `create_partner_and_report` не переписывать (только при необходимости минимально).

## 7. Must-preserve invariants
- Внешние вызовы (sidecar, LLM) БЕЗ открытой DB-транзакции: commit состояния → внешний вызов → commit результата. Никаких row locks на время вызовов.
- `deterministic_payload_json` сохраняется и коммитится ДО LLM-фазы (LLM retry не пересчитывает эфемериды).
- `report.attempt_count` инкрементируется на каждую LLM-попытку и никогда > 2 (текущая семантика поля — LLM attempts).
- Owner-scoped поведение остальных методов (get/drilldown/feedback/delete) не меняется.
- GRACE-разметка файла (AI_HEADER / MODULE_CONTRACT / START_BLOCK / FUNCTION_CONTRACT) сохраняется и обновляется по факту; новые события логирования — только из registry (`apps/api/app/core/logging_events.py`), если нужного события нет — использовать существующие `synastry.*` из MODULE_CONTRACT, новые НЕ выдумывать без записи в отчёте.
- Логи без PII (имена партнёров, даты рождения не логировать).

## 8. Контракты и указатели (использовать, не изобретать)

**Sidecar** — `POST {settings.solarsage_url}/v1/synastry` (`apps/api/app/core/config.py:150`, дефолт `http://127.0.0.1:18091`):
- Request/response schema: `apps/solarsage/solarsage/schemas/synastry.py` (`SynastryRequest`, `SynastryResponse.cross_aspects[]`: `owner_planet, partner_planet, aspect_type, orb_degrees, applying`; `precision_flags`).
- Owner birth data — из `UserProfile` (`birthday: date`, `birth_time: time|None`, lat/lon/tz поля — см. `apps/api/app/db/models.py` класс UserProfile, ~строки 219+). Partner — из `SynastryPartner` (birth_date/birth_time/birth_lat/birth_lon/birth_tz/precision).
- HTTP-паттерн с httpx + обработка ошибок: `apps/api/app/services/natal_context_service.py` (`_build_natal_context`, ~строки 332-360). Timeout разумный (30-60 c).
- Маппинг: `cross_aspects` → `RawAspectInput(owner_planet, partner_planet, aspect_type, orb_degrees)` → `SynastryScoringEngine.calculate_score(aspects, partner_time_precision=partner.precision)`.

**LLM** — паттерн `apps/api/app/services/llm/service.py` (LLMService); prompt — `build_report_prompt` (`apps/api/app/services/synastry_llm.py:126`); ответ парсить как JSON и валидировать `validate_llm_output(data, report_precision=partner.precision)`. Невалидный/пустой ответ = неудачная попытка (retry один раз в пределах attempt_count ≤ 2, затем failed + refund).

**Refund** — модель `SynastryCreditSpend` (`apps/api/app/db/models.py:1502-1544`): найти spend по `report_id`, `credit.used_amount -= 1`, `spend.refunded_at = datetime.now(timezone.utc)`, один commit вместе с `state="failed"`.

**Существующая структура** — текущий `run_report_pipeline` (`synastry_service.py:203-323`) уже содержит правильный скелет state/commit'ов и сериализацию det_payload: сохранить скелет, заменить источник aspects и источник narrative.

## 9. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_synastry_service.py -q
python3 scripts/grace_lint.py apps/api/app   # из корня репо; обязателен PASS
```
Тесты обновить под реальный pipeline: мок httpx sidecar-вызова и LLM-вызова (см. существующие мок-паттерны в `apps/api/tests/`, напр. test_synastry_service.py и тесты natal/horary). Кейсы минимум: happy path ready; sidecar down → failed + refund; LLM invalid ×2 → failed + refund, attempt_count=2.

## 10. Expected evidence
- `git diff --name-only` — ровно 2 файла из scope.
- Вывод pytest (все зелёные) и grace_lint PASS.
- В отчёте: какой LLM-метод/клиент переиспользован, какие error_code введены.

## 11. Escalation rule
Нужен соседний scope (models/миграция, sidecar, api/, frontend) → стоп, доложить, новый packet.

## 12. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
