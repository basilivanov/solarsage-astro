# 35 TZ W6-S4b — O1-pregen: typed outcomes, retry, current+tomorrow, telemetry

1. **Packet title**: W6-S4b-O1-PREGEN-TELEMETRY
2. **Phase / Wave**: W6-FOCUS-HARDENING, срез S4b (backend/infra). Normative
   source: `29_TZ_W4_O1_PREGEN_CACHE_RELIABILITY.md` («doc 29») — реализуются
   §2.6/§2.7, §4.5, §4.6, §6 (tests 9–12), §7. Зависит от W6-S4a (quality
   predicate и contentState-матрица уже в main).
3. **Modules**: M-DAY-PREGEN (jobs/day_pregen.py), M-LOGGING (registry),
   M-DAY-SERVICE.audit, Makefile/systemd sources.
4. **Goal**: pregen считает честные typed outcomes, ретраит transient-сбои,
   прогревает current И tomorrow для каждой user-local даты, логирует без
   персональных данных; batch exit status отражает неполное покрытие.

## 5. Exact write scope

- `apps/api/app/jobs/day_pregen.py` — typed outcome per user/date
  (§4.5 doc 29): `cache_hit | complete | unavailable_retryable |
  failed_retryable | failed_terminal | skipped_ineligible`.
  `complete` = factual payload + допустимый contentState по матрице S4a;
  `unavailable` НИКОГДА не complete. Bounded retry с backoff/jitter и
  max attempts для transient (provider/timeout). Per-user ошибка не роняет
  batch, но summary + exit code отражают coverage. Обе даты: current
  (`days_ahead=0`) и tomorrow (`days_ahead=1`) — если CLI один `--days-ahead`,
  canonical runner вызывает дважды; DST/IANA per user (уже есть — проверить
  тестом §6.10).
- `apps/api/app/core/logging_events.py` (+ frontend `lib/log/events.gen.ts`
  ТОЛЬКО если там держится тот же registry — проверить; backend достаточно) —
  registry-first события §7 doc 29: `day.convergence_built`,
  `llm.call_completed`, `day.pregen_item_completed`,
  `day.pregen_batch_completed` с безопасными полями. Потом использование в
  коде (today_service/llm_service/pregen).
- `apps/api/tests/test_day_pregen*.py` — outcomes, retry, coverage exit code,
  две даты/таймзоны/DST, no-PII лог-тест (§6.9–6.11).
- `Makefile` — при необходимости target для двухдатного pregen dry-run.
- `infra/systemd/` — ТОЛЬКО если canonical timer unit должен вызывать job
  дважды (0 и 1): обновить source unit + комментарий (deploy на хост делает
  ревьюер вручную, не кодер).

## 6. Frozen / Out of scope

- today_service/llm_service provider internals — S4a уже принят, здесь только
  вызовы лог-событий если потребуется (минимальные diff).
- Удаление legacy eager генерации, production orchestrator changes (doc 29 §8).
- Raw user.id/Telegram ID/username/birth data/UUID в stdout/stderr/logs —
  ЗАПРЕЩЕНО (§2.7, §4.5): только hashed user key (уже есть/добавить
  deterministic hash helper, не loggable reverse).
- Frontend — не трогать.

## 7. Must-preserve invariants

- Полный pytest suite зелёный; grace_lint PASS; ruff/mypy чисто.
- Одинаковые flags/versions/timezone/cache key у API и pregen (§2.6) —
  pregen вызывает тот же TodayService path.
- Retry только transient; `failed_terminal` (schema/validation) без retry.
- Coverage threshold: batch не success при incomplete coverage (порог
  задокументировать, предложить fail если complete+cache_hit < 99% selected
  ИЛИ любой failed_terminal — точную политику изложить в отчёте).
- Существующее поведение `solarsage-day-pregen.timer` не ломается (он
  ежедневный 04:07, unit несёт valence flag — не трогать флаги).

## 8. Verification

```bash
cd apps/api && source .venv/bin/activate && \
python -m pytest tests/ -q -k "pregen or logging or cache" && \
python -m pytest tests/ -q -k "not postgres and not election_quota_persists" && \
ruff check app/ && mypy app/services/ app/jobs/ && python3 ../../scripts/grace_lint.py app
```

## 9. Expected evidence

- Pregen batch report (synthetic users, current+tomorrow), retry outcomes
  matrix, exit codes по сценариям, пример логов (0 PII — scanner output),
  diff registry events, git diff --stat.

## 10. Escalation

Нужен production orchestrator change, удаление V1/V2 rows, новая модель —
стоп (doc 29 §8).

## 11. No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
