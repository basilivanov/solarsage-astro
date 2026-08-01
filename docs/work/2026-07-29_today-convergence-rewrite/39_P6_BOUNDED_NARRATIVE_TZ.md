# 39 — P6 BOUNDED NARRATIVE TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
в tmux astro2:0.0 (cwd `/tmp/solarsage-convergence-impl`, модель gpt-5.6-luna).

## 1. Packet title

P6 (W6) — bounded narrative generation: один strict-JSON LLM call на
`(snapshot_id, prompt_version)` с claim binding, capability gate и честным
`unavailable` без template fallback.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P6 (W6 bounded narrative). Зависит от уже
принятых P3-F (narrative lease, коммит 12c56fea) и P4-D1 (wire projection,
коммит 397a1278). Lease orchestration и HTTP-подключение — НЕ этот packet
(P4-D2 следом).

## 3. Modules

- Новый: `M-TODAY-NARRATIVE` — apps/api/app/services/today_narrative_service.py
- Изменяемые: `apps/api/app/core/config.py` (typed settings),
  `apps/api/app/core/logging_events.py` (3 новых события)
- Тесты: `apps/api/tests/test_today_narrative_service.py`

## 4. Goal

Сервис, который по опубликованному `TodaySnapshot` строит bounded prompt
(только selected public units + capabilities, НЕ весь ledger ~150 факторов),
выполняет один strict-JSON LLM call с `max_output_tokens=700` и hard deadline,
валидирует ответ (schema + claim binding + capability gate + summary ≤220) и
возвращает либо валидный `content_json` для `complete_ready`, либо typed
failure для `complete_unavailable`. Никакого template fallback copy.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/05_W5_W8_OPERATIONS_AND_RELEASE_TZ.md`
  §3 (LLM contract, строки 124-154) и §4 (content-cap gate, строки 170-183).
- `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §3.3 (строки 144-229): claim shape `{text, sourceEventIds}`, summary ≤220,
  вложенные caps.
- Существующий lease API: `apps/api/app/services/today_narrative_lease_service.py`
  (`acquire/complete_ready/complete_unavailable/load`) — использовать как
  consumer-контракт, НЕ менять.
- Projection-сторона (как content_json читается):
  `apps/api/app/services/today_convergence_projection.py` `_apply_narrative`
  (:668-702) и `_claim` (:639-657).

## 6. content_json canonical форма (фиксируется этим packet)

Producer пишет Mapping-форму (projection её уже поддерживает):

```json
{
  "convergences": {"<group_id>": {"summary": {"text": "...", "sourceEventIds": ["evt_v1_..."]} | null,
                                  "meaning": {...} | null, "action": {...} | null}},
  "main_event": {"summary": ..., "meaning": ..., "action": ...} | null,
  "impulses": {"<event_id>": {"summary": ..., "meaning": ..., "action": ...}}
}
```

- Ключи `convergences`/`impulses` — ровно ID выбранных блоков snapshot;
  отсутствующий блок = null-поля (не ошибка).
- Каждый claim: `text` непустой; `sourceEventIds` непустой подмассив
  deterministic event IDs ЭТОГО блока (convergence → `evidence_event_ids`,
  main_event/impulse → собственный `event_id`).
- `summary.text` ≤ 220 chars; 221 отклоняет ВЕСЬ narrative (без обрезки).

## 7. Exact write scope

- `apps/api/app/services/today_narrative_service.py` (новый)
- `apps/api/tests/test_today_narrative_service.py` (новый)
- `apps/api/app/core/config.py` — только добавить typed settings:
  `today_narrative_max_output_tokens: int = 700` (alias
  `TODAY_NARRATIVE_MAX_OUTPUT_TOKENS`), `today_narrative_timeout_seconds`
  (alias `TODAY_NARRATIVE_TIMEOUT_SECONDS`, default 45 hard deadline;
  provider-level цель 30s остаётся конфигурацией вызова),
  `today_narrative_prompt_version: str` (alias `TODAY_NARRATIVE_PROMPT_VERSION`,
  default `"today-narrative-v2"` after the strict per-snapshot response-template
  correction; v1 rows remain immutable and are not rewritten).
- `apps/api/app/core/logging_events.py` — добавить ровно 3 события:
  `day.narrative_generation_started`, `day.narrative_generation_completed`,
  `day.narrative_generation_failed`.
- Если registry имеет generated/frontend sync (проверить
  `scripts/check_logging_guardrails.py` и `lib/log/events.gen.ts` generator) —
  выполнить существующую команду синхронизации и приложить результат.

## 8. Frozen / Out of scope

- НЕ менять: lease service, projection, snapshot service, schemas, endpoints,
  миграции, frontend, canon YAML, legacy `llm_service.py`.
- НЕ реализовывать: HTTP endpoints, BackgroundTasks wiring, pregen job,
  retry/cooldown политику (это lease + P4-D2/P5).
- НЕ вызывать реального LLM-провайдера в тестах (только mock/fake client).

## 9. Функциональные требования

### 9.1 Prompt construction (bounded)

- В prompt идут ТОЛЬКО: selected convergences (group_id, сферы, polarity,
  evidence_event_ids с их kind/sphere/polarity/EventTime из factor_units),
  main_event, impulses, `dayTone`, `birthTime.capabilities` и
  `birthTime.mode`. Запрещено включать полный `factor_units` ledger,
  audit-блоки, profile fields, raw birth data.
- Язык выхода — русский (как остальные today-тексты). Время/окна в тексте
  LLM запрещены: время приходит из deterministic EventTime (указать это в
  prompt-инструкции).
- `prompt_version` участвует в identity вызова (lease key) и логах.

### 9.2 LLM call

- Использовать существующий provider client слой (`services/llm/client.py`
  или эквивалентный существующий); если он не поддерживает strict JSON
  response_format — допустим prompt-based strict JSON + parse, но схема
  обязана валидироваться полностью (см. 9.3). Новых зависимостей не
  добавлять без эскалации.
- `max_output_tokens = settings.today_narrative_max_output_tokens` (700).
- Один вызов на snapshot/prompt_version; provider fallback допустим только
  внутри общего bounded deadline (45s hard), без параллельных вызовов.
- Timeout/transport/schema/claim/capability failure → typed failure с
  `error_code` из фиксированного enum (например `timeout`, `schema_invalid`,
  `claim_binding`, `capability_violation`, `provider_error`) — он пойдёт в
  `complete_unavailable(error_code=...)`.

### 9.3 Validation (принимается только целиком)

1. JSON parse + schema: точные ключи блоков, claim shape, text непустой.
2. Claim binding: каждый `sourceEventIds` ⊆ event IDs своего блока;
   непустой; без дублей. Любое нарушение → reject всего narrative.
3. `summary.text` ≤ 220 (иначе reject всего narrative).
4. Capability gate: при `birthTime.mode != "exact"` текст любого claim НЕ
   должен содержать ссылки на дома/ASC/MC/lots/точные часы. Реализовать как
   deterministic banned-pattern проверку (RU+EN: "дом", "дома", "асцендент",
   "ASC", "MC", "лот", "жребий", "house", "ascendant", HH:MM паттерн).
   При `exact` HH:MM в тексте тоже запрещены (время только из EventTime),
   дома/ASC/лоты разрешены к упоминанию только если capabilities=true.
   Нарушение → reject всего narrative с `capability_violation`.
5. Неизвестные block IDs в ответе (ID, которого нет в snapshot) → reject.

### 9.4 Structured logging (P0-G)

- На границах генерации: `day.narrative_generation_started` (с snapshot_id,
  prompt_version, block counts), `..._completed` (latency_ms, claims count,
  output_tokens если доступен), `..._failed` (error_code, latency_ms).
- Через существующий `log_event`/`bind_log_context` из `app/core/logging.py`;
  slice/module/block точные; correlation_id пробрасывается из caller'а через
  параметр (не генерировать молча). PII/LLM text в логах запрещены — только
  counts/ids/latency.
- Ошибка логгера не ломает flow (guard).

### 9.5 Публичный интерфейс (рекомендуемый)

```python
@dataclass(frozen=True)
class TodayNarrativeSuccess: content_json: dict; output_tokens: int | None; latency_ms: int
@dataclass(frozen=True)
class TodayNarrativeFailure: error_code: str; latency_ms: int

async def generate_today_narrative(
    snapshot: TodaySnapshot, *,
    prompt_version: str,
    llm: <injectable protocol>,  # тесты подставляют fake
    correlation_id: str | None = None,
    clock/timeout injection по необходимости,
) -> TodayNarrativeSuccess | TodayNarrativeFailure
```

DB/lease внутри НЕ трогать — чистая генерация+валидация. Lease вызовет
consumer (P4-D2).

### 9.6 GRACE

Полная разметка (AI_HEADER/MODULE_CONTRACT/MODULE_MAP/owned_tests,
FUNCTION_CONTRACT на публичных, START_BLOCK: PROMPT/CALL/VALIDATE/CAPABILITY/
LOGGING). `emitted_logs` в contract = 3 реальных имени из §7.

## 10. Must-preserve invariants

- `python3 scripts/check_logging_guardrails.py` — PASS.
- `pnpm contracts:check` не затрагивается (backend-only change).
- Существующие 2540+ backend тестов остаются зелёными.
- Legacy `TodayService`/LLM path не меняется (W9 позже).

## 11. Verification

```bash
cd /tmp/solarsage-convergence-impl/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_narrative_service.py -q -p no:cacheprovider
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check app/services/today_narrative_service.py app/core/config.py app/core/logging_events.py
cd /tmp/solarsage-convergence-impl && python3 scripts/grace_lint.py apps/api/app/services/today_narrative_service.py && python3 scripts/check_logging_guardrails.py
# полный не-регресс:
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -3
```

## 12. Expected evidence

Обязательные тест-кейсы (fake LLM client):

- happy path convergence_today (3 группы) и quiet_day (mainEvent + 3 impulses):
  валидный content_json, claim binding принят;
- claim с чужим event ID / пустой список / дубли → reject целиком;
- summary 220 chars принят, 221 → reject целиком;
- bucket/unknown mode: текст с "дом"/"ASC"/"15:40" → capability_violation;
  exact mode: текст с "15:40" → violation; текст про дома при
  capabilities.houses=false → violation;
- unknown block ID в ответе → reject;
- невалидный JSON / пропущенные обязательные блоки → schema_invalid;
- timeout и provider error → typed failure с latency;
- prompt НЕ содержит полного ledger (assert: количество evt_v1 в prompt ≤
  selected count; audit/profile ключи отсутствуют);
- max_output_tokens=700 передаётся в вызов (assert на fake client);
- логи: 3 события эмитятся с ожидаемыми полями (caplog/перехват), ошибка
  логгера не ломает результат.

## 13. Escalation rule

Нужно менять lease/projection/schemas/endpoints или добавлять новую
зависимость → СТОП, доложить, новый packet. Соседние замечания — в отчёт,
не в scope.

## 14. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер. `git status` в конце:
только файлы из §7.
