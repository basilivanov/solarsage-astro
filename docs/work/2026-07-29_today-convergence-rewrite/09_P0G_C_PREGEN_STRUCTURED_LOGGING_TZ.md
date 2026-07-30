# P0-G-C — Structured logging существующего day pregen

Phase / Wave: `today-convergence-2 / P0-G`

Modules: `M-JOBS-DAY-PREGEN`, `M-TEST-JOBS-DAY-PREGEN`

## Goal

Заменить три raw `print()` в существующем nightly `day_pregen` на события,
зарегистрированные packet 08, не меняя его selection/cache/runtime-поведение.
Наблюдаемый результат — batch start, каждый user/date outcome и batch summary
пишутся через canonical `log_event`, а raw user identifiers и exception text не
попадают в лог.

## Exact write scope

- `apps/api/app/jobs/day_pregen.py`
- `apps/api/tests/test_day_pregen_job.py`

## Frozen / Out of scope

- event registry и logging/redactor implementation;
- TodayService, AccessService, cache identity и DB models;
- systemd timer/service;
- W5 snapshot leases/pregen topology;
- CLI arguments и публичный tuple return contract `(ok, skipped, failed)`;
- guardrail discovery и CI workflow.

## Must preserve

- выбор active users и вызов только canonical
  `TodayService.get_today_payload` остаются прежними;
- per-user failure не прерывает batch;
- `ok` означает legacy completed path `duration > 1s`, `skipped` — legacy
  `fast_path <= 1s`; это не переименовывается в cache hit;
- duration измеряется monotonic clock и публикуется как неотрицательный
  `duration_ms`;
- `day.pregen_started` публикуется один раз после selection;
- `day.pregen_user_finished` публикуется ровно один раз на user/date с
  `outcome=completed|fast_path|failed`; failure несёт только `error_type`, без
  exception message;
- `day.pregen_completed` публикуется ровно один раз с итоговыми
  `completed/fast_path/failed`;
- standalone job задаёт точные GRACE context fields: slice, module, block,
  correlation_id; для user-level контекста допустим только `hash_user_id`, raw
  `user.id`/`tg_user_id` запрещены;
- в production module нет вызовов builtin `print()` и импорта `sys`;
- module/function contracts обновлены реальными `emitted_logs`, а MODULE_MAP
  ссылается на новый owned test;
- новый test-файл имеет обязательную GRACE-разметку.

## Verification

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_day_pregen_job.py -q
cd ../.. && python3 scripts/check_logging_guardrails.py
```

## Expected evidence

- diff только двух разрешённых файлов;
- targeted pytest: happy/fast/failure paths, exact event multiplicity and
  payloads, return tuple, no raw identifier/exception text leakage;
- logging guardrails: PASS;
- список реально emitted событий.

## Escalation

Если для тестируемого результата требуется менять registry, logging API,
TodayService или production topology, остановиться и доложить: это отдельный
packet.

## No commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
