# 04_TZ: Синастрия — реальный drilldown + обогащение narrative (срез D)

## 1. Packet title
Синастрия — drilldown через LLM + поля verdict/hero в report narrative. Срез D из 4. Зависит от принятого среза A.

## 2. Phase / Wave
W-SYNASTRY-MVP, fix-wave: pipeline wiring.

## 3. Modules
- M-SYNASTRY-SERVICE (`apps/api/app/services/synastry_service.py`)
- M-LLM-SYNASTRY (`apps/api/app/services/synastry_llm.py`)

## 4. Goal
Две связанные доработки:

**4.1. Реальный drilldown.** `SynastryService.get_aspect_drilldown` сейчас возвращает заглушку (всегда Sun/Moon/trine). Сделать по-настоящему:
1. Найти аспект по `aspect_id` в `report.deterministic_payload_json` (`aspects[]`, поле `id`); не найден → 404.
2. Если `SynastryAspectDetail` с payload нет — построить prompt через `build_drilldown_prompt(aspect)` (`synastry_llm.py:167`), вызвать LLM (паттерн `_generate_llm_narrative`: system+user конкатенацией, `LLMClient`), распарсить JSON, валидировать `validate_drilldown_output` (`synastry_llm.py:225`).
3. Сохранить в `synastry_aspect_details` (state='ready', attempt_count+1), вернуть `AspectDrilldown`. Маппинг LLM-полей → AspectDrilldown согласовать со схемой `app/schemas/synastry.py` (если полей не хватает — стоп, эскалация).
4. LLM-ошибка → detail state='failed', НИКАКИХ изменений READY base report и НИКАКОГО spend/refund (инвариант master TZ 10.2).

**4.2. Narrative enrichment.** `build_report_prompt` просит у LLM `summary/aspect_shorts/translations/spheres`, но API-контракт читает из narrative ещё `verdict/hero_title/hero_description` (сейчас всегда дефолтные). Дописать в user-prompt запрос полей `verdict` (до 120 символов), `hero_title` (до 60), `hero_description` (до 220) — так, чтобы `validate_llm_output` их пропускал (длины при необходимости добавить в проверки, не ослабляя существующие).

## 5. Exact write scope
- `apps/api/app/services/synastry_service.py` (только `get_aspect_drilldown` + при необходимости хелпер)
- `apps/api/app/services/synastry_llm.py` (только `build_report_prompt` + при необходимости доп. проверки длин в `validate_llm_output`)
- `apps/api/tests/test_synastry_service.py` (drilldown-кейсы)
- `apps/api/tests/test_synastry_llm.py` (prompt/validation кейсы)

## 6. Frozen / Out of scope
- НЕ трогать `run_report_pipeline` (принят в A), api/, models, sidecar, frontend.
- НЕ менять формат `deterministic_payload_json`.
- НЕ трогать кредиты: drilldown бесплатный по спеке.

## 7. Must-preserve invariants
- Failure drilldown НЕ меняет READY base report (master TZ 10.2).
- Все существующие тесты остаются зелёными; изменения prompt'а обратно-совместимы с `validate_llm_output`.
- Prompt'ы без PII; логи только registry-события, без PII.
- GRACE-разметка обновляется по факту.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m pytest tests/test_synastry_service.py tests/test_synastry_llm.py -q
python3 scripts/grace_lint.py apps/api/app   # из корня репо; обязателен PASS
```

## 9. Expected evidence
- `git diff --name-only` — ровно файлы из scope.
- Вывод pytest (зелёный) и grace_lint PASS.
- В отчёте: маппинг LLM-ответа → AspectDrilldown.

## 10. Escalation rule
Нужны изменения схемы AspectDrilldown / models / api → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
