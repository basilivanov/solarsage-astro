# M1 TZ: структурированный персональный разбор сферы (drilldown) в concrete advice

Дата: 2026-07-27
Phase / Wave: **W-TODAY-SPHERE-WHY-MODALS**, срез M1 (backend)
Контекст: `docs/work/2026-07-27_today-premium-first-screen/00_MASTER_TZ.md` + живой фидбек владельца:
тексты сфер — одно шаблонное предложение («Действуй активно…») при богатом evidence (97–161 факторов/сферу).
Modules: `M-API-LLM-SERVICE`, `M-API-TODAY-INTERPRETATION-SERVICE`, `M-SCHEMAS-TODAY`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Goal (один наблюдаемый результат)

Каждая из 12 сфер в `concreteAdvice.rows[]` получает аддитивное поле
`details: { story, why[], advice } | null` с персональным, grounded в
evidence содержимым. Существующее `row.text` и весь текущий контракт не
меняются (обратная совместимость: старые кеши/клиенты работают).

## 2. Целевая структура (на сферу)

- `story: string` — 2–3 предложения о ЧЕЛОВЕКЕ и его дне в этой сфере:
  узнаваемая жизненная сцена, не инструкция. Запрещены: астротермины
  (транзит/аспект/орб/натал/планеты по именам), фатализм, «может произойти»,
  канцелярит («используйте благоприятные аспекты»), второе лицо мн.ч.
- `why: string[]` — 1–2 строки «что за этим стоит»: причина из evidence
  человеческим языком (например: «долгий цикл про статус и сроки усилился
  в эти недели, а сегодня его задел быстрый триггер»). Grounded в
  переданном evidence; нельзя выдумывать факты жизни.
- `advice: string` — один короткий конкретный совет (до ~120 символов).

## 3. Exact write scope

- `apps/api/app/services/llm_service.py` — `generate_concrete_advice`:
  промпт → структурированный JSON-вывод на 12 сфер
  `{ "<key>": { "story": ..., "why": [...], "advice": ... } }`, парсинг,
  retry/валидация формы. Сохранить обратную совместимость: из того же
  ответа собирать legacy `row.text` (например, story→text при отсутствии
  отдельного поля, либо advice — выбрать и зафиксировать одно правило в
  FUNCTION_CONTRACT).
- `apps/api/app/schemas/today.py` — `ConcreteAdviceRow`: добавить
  `details: ConcreteAdviceDetails | None = None`
  (`ConcreteAdviceDetails{story: str, why: list[str], advice: str}`).
- `apps/api/app/services/today_interpretation_service.py` — применение
  attempt: заполнение `row.details` с валидацией через существующий
  LLMClaimValidator (расширить при необходимости минимально); честный
  fallback: details=None (НЕ выдумывать).
- `apps/api/app/services/llm_claim_validator.py` — валидация story/why/advice
  (бан-лист терминов/фатализма), только если это естественно ложится в
  существующую структуру.
- Тесты: `apps/api/tests/services/test_llm_service*.py`,
  `apps/api/tests/services/test_today_interpretation*.py` — по месту
  существующих тестов этого контура.

## 4. Frozen / out-of-scope

- Scoring, valence, verdicts, counts, day_status (это W2 — отдельная волна).
- Frontend (M2/M3 отдельно).
- Пер-планетные интерпретации, whyToday, horizons.
- Изменение числа LLM-вызовов: остаётся ОДИН вызов на 12 сфер.
- Изменение модели/провайдера/таймаутов LLM.

## 5. Must-preserve инварианты

- Attempt acceptance: не хуже текущего (≥9 валидных rows); отклонённый
  attempt не трогает rows.
- `row.text`, verdict, counts, evidence — без изменений семантики.
- Payload cache identity не ломать: добавление поля в ответ не должно
  инвалидировать/портить чтение старых кешей (details отсутствует → null).
- GRACE-разметка в изменённых файлах обновлена; новые события — только из
  registry (`apps/api/app/core/logging_events.py`), без новых имён без
  необходимости.
- В логах никаких персональных данных.

## 6. Verification (одна targeted-команда)

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/services/ -q -k "concrete_advice or interpretation or llm_service"
```

## 7. Expected evidence

- Список файлов, вывод verification.
- Пример сгенерированного details для 2 сфер (из unit-теста или ручного
  прогона с моком LLM) — текстом в отчёте.

## 8. Escalation rule

Нужен файл вне §3, изменение scoring/valence, второй LLM-вызов — стоп,
доложить. Ничего не коммить и не пушить.
