# 34 TZ W6-S4a — O1-core: bounded Today path, schema invariants, honest cache

1. **Packet title**: W6-S4a-O1-CORE-BOUNDED-CACHE
2. **Phase / Wave**: W6-FOCUS-HARDENING, срез S4a (backend). Normative source:
   `29_TZ_W4_O1_PREGEN_CACHE_RELIABILITY.md` (далее «doc 29») — обязателен;
   реализуются §2 (инварианты 1–5), §3 (bounded execution), §4.1/§4.2/§4.3,
   часть §6 (tests 1–8). Pregen/retry/telemetry — отдельный срез S4b.
3. **Modules**: M-DAY-SERVICE (today_service), M-LLM-SERVICE (provider
   boundary), M-SCHEMAS-TODAY-FOCUS (validators), M-CACHE (quality predicate).
4. **Goal**: один absolute request deadline на все LLM-операции Today;
   focus narrative внутри bounded phase (нет второго post-wait await);
   при любом LLM-сбое facts сохраняются с `contentState="unavailable"` и null
   LLM-полями; cache hit только при quality-валидном contentState.

## 5. Exact write scope

- `apps/api/app/services/today_service.py` — request-local `deadline_at`
  (из существующего `TODAY_LLM_PHASE_DEADLINE_SECONDS`, один бюджет на ВСЮ
  LLM-фазу включая focus); focus narrative перенести в bounded task group;
  удалить отдельный post-wait `await generate_focus_narrative()`; quality
  predicate в `_get_cached_payload`/`_cache_payload` (§2.5 doc 29).
- `apps/api/app/services/llm_service.py` — OPTIONAL `deadline_at`/remaining
  budget аргумент на `_generate_text`/provider helpers; прежнее поведение по
  умолчанию для непромигрированных callers (doc 29 §4.2: Horary/Natal/Synastry
  contract НЕ меняется); cancellation-safe: при CancelledError client
  закрывается, отмена пробрасывается, следующий provider не стартует; fallback
  provider только при достаточном remaining budget.
- `apps/api/app/schemas/today_focus.py` — Pydantic validator матрицы
  state×content_state (таблица §4.3 doc 29) + caps events<=3,
  featured_spheres<=3, no duplicate public IDs, непустые IDs.
- `apps/api/tests/` — новые тесты из §6 doc 29 п.1–8 в существующих файлах
  today_service/llm/cache тестов + negative schema tests в
  `test_today_focus_contract.py`.
- `packages/contracts/*` — регенерация ТОЛЬКО если изменился OpenAPI
  (validators не меняют схему; скорее всего regen не нужен — проверить
  `npm run contracts:generate` и не коммитить пустой drift).

## 6. Frozen / Out of scope

- Формулы расчёта, selector (W6-S1), sidecar — не трогать.
- `day_pregen.py`, Makefile, telemetry registry — S4b.
- Удаление eager legacy генерации (headline/reading/why) — НЕ этот срез
  (doc 29 §3.1: они остаются, но внутри общего budget и без права продлить
  focus deadline; legacy результат не переводит focus unavailable→ready).
- Generic `_generate_text` default policy для других фич — не менять
  (doc 29 §4.2 caller audit clause).
- Frontend — не трогать.

## 7. Must-preserve invariants

- Полный pytest suite зелёный: Horary/Natal/Synastry LLM callers — прежний
  contract (regression evidence в отчёте).
- Facts-first: deterministic focus/events/state возвращаются даже при
  timeout/provider error; все LLM-owned поля null при сбое (§2.3/§2.4).
- Cache matrix (§6.7): `unavailable`/`pending`/missing focus/old content
  version → miss; valid `ready` (convergence_today/single_impulses) и
  `not_needed` (background_only/no_accent) → hit. Fresh build и cache hit
  дают одинаковые focus state/event IDs/order/featured IDs (§6.8).
- Schema: пары `convergence_today+not_needed`, `background_only+ready` и т.п.
  отклоняются validator'ом (negative tests).
- grace_lint PASS, ruff/mypy чисто.

## Дизайн-заметки (обязательны)

- `deadline_at = monotonic() + TODAY_LLM_PHASE_DEADLINE_SECONDS` один раз на
  request; внутрь передаётся remaining = deadline_at - now; provider attempt
  timeout = min(60, remaining); fallback только если remaining достаточно для
  полного запроса+валидации (порог задокументировать, предложить ≥ 15s).
- По истечении deadline: отменить незавершённые задачи и собрать через
  `asyncio.gather(..., return_exceptions=True)` — никаких фоновых платных
  запросов после ответа (§2.1, §6.4).
- Focus failure fail-closed атомарно: facts остаются, summary/meanings/
  featured copy = null, `content_state="unavailable"`, никакого шаблонного
  текста (§2.4).
- Время: prompt/evidence не форматирует UTC через strftime("%H:%M") —
  проверить и убрать, если есть (§3.3).
- НЕ добавлять новые log events в этом срезе (registry — S4b); использовать
  существующие.

## 8. Verification

```bash
cd apps/api && source .venv/bin/activate && \
python -m pytest tests/ -q -k "today_focus or cache or llm or today_service" && \
python -m pytest tests/ -q -k "not postgres and not election_quota_persists" && \
ruff check app/ && mypy app/services/ && python3 ../../scripts/grace_lint.py app
```

## 9. Expected evidence

- Before/after latency trace (deterministic vs LLM vs provider) на cache-miss
  кейсе, доказательство cancellation (нет leaked tasks), provider attempt
  count ≤ budget, cache hit/miss matrix по state/contentState/version,
  parity fresh-vs-cached (IDs/order), caller-audit note для non-Today LLM
  callers, git diff --stat.

## 10. Escalation

Нужно менять generic default timeout для всех callers, удалять legacy eager
генерацию, менять wire schema, второй LLM-вызов — стоп (doc 29 §8).

## 11. No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
