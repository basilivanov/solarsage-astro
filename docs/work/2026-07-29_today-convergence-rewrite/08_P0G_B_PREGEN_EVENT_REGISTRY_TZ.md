# P0-G-B — Registry событий legacy day pregen

Phase / Wave: `today-convergence-2 / P0-G`

Modules: `M-OBSERVABILITY-EVENTS`, `M-JOBS-DAY-PREGEN`

## Goal

Добавить в закрытый GRACE registry минимальный lifecycle-контракт для
существующего nightly `day_pregen`, чтобы следующим локальным срезом заменить
raw `print()` на типизированные структурные события. Наблюдаемый результат —
XML, Python и TypeScript registry содержат один и тот же набор из трёх новых
событий и проходят drift gate.

Новые события:

- `day.pregen_started` — batch выбран и запускается;
- `day.pregen_user_finished` — одна user/date операция закончилась с исходом
  `completed | fast_path | failed`;
- `day.pregen_completed` — итоговые счётчики batch.

`fast_path` в этом legacy-контракте означает только завершение менее чем за
текущий порог job. Это **не** утверждение о cache hit. Настоящая snapshot/pregen
семантика будет введена в W5 отдельным packet.

## Exact write scope

- `grace/canon/observability.xml`
- `apps/api/app/core/logging_events.py`
- `lib/log/events.gen.ts`

## Frozen / Out of scope

- `apps/api/app/jobs/day_pregen.py` и любые callsites;
- logging API, redactor и guardrail discovery;
- TodayService/cache contracts;
- CI workflow;
- новые snapshot/pregen события W5.

## Must preserve

- три registry остаются множественно идентичными;
- существующие event names и payload contracts не меняются;
- новые payload не содержат user ID, Telegram ID, birth data, exception text
  или другой PII;
- `day.pregen_started`: `users_total`, `days_ahead`, `concurrency` — required
  number;
- `day.pregen_user_finished`: `outcome` — required enum
  `completed,fast_path,failed`; `duration_ms` — required number;
  `error_type` — optional string;
- `day.pregen_completed`: `completed`, `fast_path`, `failed` — required number;
- generated Python/TypeScript registry не получают runtime-логику.

## Verification

```bash
python3 -c 'import importlib.util, pathlib; p=pathlib.Path("scripts/check_logging_guardrails.py"); s=importlib.util.spec_from_file_location("logging_guardrails", p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert m.check_registry_drift()'
```

## Expected evidence

- diff только трёх разрешённых registry-файлов;
- вывод `drift gate: OK`;
- перечень новых событий и их payload fields.

## Escalation

Если требуется менять logging emitter, generator tooling, callsites или
существующие события, остановиться и доложить: это соседний scope и новый
controller packet.

## No commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
