# S1 TZ: no-fallback policy — честная недоступность + алерты вместо тихих перезаписей

Дата: 2026-07-28
Phase / Wave: **W-DAY-HONEST-UNAVAILABLE**, срез S1
Modules: `M-API-LLM-CLAIM-VALIDATOR`, `M-API-TODAY-INTERPRETATION-SERVICE`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Проблема

`LLMClaimValidator.validate_concrete_advice_text` при срабатывании hard-guard
(вредный совет на avoid-вердикте: «инвестируй», «выясняй отношения»,
«интенсивная тренировка») МОЛЧА перезаписывает текст рукотворной безопасной
фразой. Это скрытый fallback: пользователь видит выдуманный текст,
команда не узнаёт, что модель ошиблась. Правило владельца: fallback-тексты
запрещены; показываем честную недоступность + алерт в логи.

`CONCRETE_ADVICE_FALLBACK_TEXT = "Рекомендация временно недоступна."` —
честное состояние, ОСТАЕТСЯ как единственный допустимый unavailable-маркер.

## 2. Goal

- Hard-guard'ы валидатора REJECT'ят текст (return None) вместо перезаписи.
- Каждый reject — структурный лог `llm.response_rejected` с `row_key` и
  machine reason code (`guard_relationships_avoid`, `guard_money_avoid`,
  `guard_body_avoid`, `banned_jargon`, `empty`, `parse`, ...). Без содержимого
  текста, без ПДн.
- Сфера с rejected текстом получает `text = CONCRETE_ADVICE_FALLBACK_TEXT`
  (честная недоступность), details=None — как сейчас при полном отказе.
- Фронт уже умеет показывать этот маркер — UI не меняется.

## 3. Exact write scope

- `apps/api/app/services/llm_claim_validator.py` — hard-guard'ы → None;
  function contract обновить (больше нет «replacement text»).
- `apps/api/app/services/today_interpretation_service.py` — per-row reject:
  log_event("llm.response_rejected", payload={row_key, reason}) по каждому
  отклонённому тексту (внутри attempt apply; при полном отказе attempt —
  одно событие с reason="attempt_rejected").
- `apps/api/tests/` — тесты валидатора и применения attempt: ожидания
  перезаписи → ожидания reject + событие.

## 4. Frozen / out-of-scope

- Промпт LLM (S2 отдельно), число вызовов, дедлайны, frontend.
- `CONCRETE_ADVICE_FALLBACK_TEXT` — не трогать (это и есть честный маркер).
- Planet/day-reading недоступности (уже честные).

## 5. Must-preserve

- attempt acceptance ≥9 валидных rows (reject не должен валить весь attempt).
- Banned-жаргон reject'ы сохраняются.
- Событие только из registry (`llm.response_rejected` уже есть — проверить,
  при отсутствии сначала добавить в registry).

## 6. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "claim_validator or concrete_advice or interpretation"
```

## 7. Expected evidence

- Файлы, вывод verification, пример лог-строки reject (без текста).

## 8. Escalation rule

Нужен файл вне §3 — стоп, доложить. Ничего не коммить и не пушить.
