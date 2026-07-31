# P1-D — Atomic Day/Calendar local-date wiring

Phase / Wave: `today-convergence-2 / P1 (W2-S0)`

Modules: `M-DAY-SERVICE.api`, `M-CALENDAR-API`, `M-CALENDAR-SERVICE`,
`M-USER-LOCAL-DATE` consumer tests.

## Goal

Перевести legacy Day, focus-event drilldown и Calendar с UTC/server date на
единый уже принятый `resolve_user_local_date(user, now)` без изменения их wire
payload. Один запрос Calendar должен использовать одну и ту же resolved local
date для range validation, `isToday` и allowed range.

## Exact write scope

- `apps/api/app/api/day.py`;
- `apps/api/app/api/calendar.py`;
- `apps/api/app/services/calendar_service.py`;
- `apps/api/tests/test_day_endpoints.py`;
- `apps/api/tests/test_calendar_endpoints.py`;
- этот packet-документ.

Если focused acceptance проще и честнее изолировать в одном новом test module,
разрешён дополнительно `apps/api/tests/test_user_local_date_consumers.py`; в
этом случае не трогать существующий test file без нужды.

## Frozen / out of scope

- Today/Calendar payload schemas и generated contracts;
- `TodayService`, convergence pipeline и birth-time/noon fallback;
- check-in, Yesterday, feedback и nightly pregen (их финальное wiring — W3/P5);
- profile/model/migrations и pure resolver implementation;
- старые Calendar status/valence semantics — они заменяются позже, не здесь;
- commits and push.

## Required behavior

- `GET /api/day/today` вызывает resolver с authenticated `User` и одним aware
  UTC instant; полученная date передаётся дальше без повторного вычисления;
- `GET /api/day/{ISO-date}` сохраняет ровно явную date и не вызывает resolver;
- `GET /api/day/today/focus-event/...` использует тот же resolver и timezone
  priority, что основной Day endpoint;
- явная ISO-date focus-event не сдвигается timezone;
- Calendar API один раз получает aware UTC instant, один раз вызывает resolver
  и использует resolved date для проверки диапазона;
- `CalendarService.get_calendar` получает resolved `today: date` явно от API;
  внутри сервиса больше нет `datetime.now(UTC).date()` для `isToday` или
  allowed-range year;
- Calendar `isToday` и `allowedRange` выводятся из одного переданного `today`;
- технический `generatedAt` остаётся UTC timestamp и не считается day
  classification;
- `UserLocalDateError` на HTTP surface превращается в безопасный 422 с code
  `INVALID_USER_TIMEZONE` и reason только из stable error code; timezone/profile
  values в ответ не попадают;
- invalid ISO format сохраняет существующий 400 `INVALID_DATE`;
- wire payload, auth/access/preview/cache behavior не меняются;
- GRACE contracts/maps/invariants/non-goals/owned_tests обновлены по факту;
- никаких новых структурных событий не требуется (`emitted_logs` не выдумывать).

## Required tests

- Day `today` west of UTC в UTC-полуночное окно использует предыдущую local
  date; east of UTC использует следующую;
- Day explicit ISO-date не вызывает resolver и не сдвигается;
- focus-event `today` запрашивает cache по resolved local date;
- Calendar на локальной границе года использует local year для range и ровно
  один day получает `isToday=true`;
- Calendar service получает `today` явно: regression guard запрещает внутренний
  UTC-date fallback;
- invalid selected timezone на Day и Calendar даёт privacy-safe 422;
- существующие Day/Calendar tests остаются зелёными.

Допустимо patch/mock-ить только системный `now` или тяжёлые downstream service
boundaries. Нельзя mock-ить сам resolver в west/east/DST acceptance: его wiring
должно быть доказано реальным helper.

## Verification

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_user_local_date.py \
  tests/test_day_endpoints.py \
  tests/test_calendar_endpoints.py -q
/opt/solarsage-astro/apps/api/.venv/bin/ruff check \
  app/api/day.py app/api/calendar.py app/services/calendar_service.py \
  tests/test_day_endpoints.py tests/test_calendar_endpoints.py
cd ../..
python3 scripts/grace_lint.py apps/api/app
python3 scripts/check_logging_guardrails.py
rg -n 'datetime\.now\(UTC\)\.date\(\)|Date\.today\(\)' \
  apps/api/app/api/day.py apps/api/app/services/calendar_service.py
git diff --check
```

Последний `rg` может оставить только комментарий/документацию; executable
совпадений быть не должно.

## Expected evidence

- local-date consumer matrix above PASS;
- no wire/generated diff;
- diff ограничен exact scope (+ optional focused test module);
- coder не коммитит и не пушит.

## Escalation

Если atomically correct wiring требует менять Today payload, convergence
pipeline, pregen или check-in, остановиться и доложить reviewer. Не добавлять
временный UTC fallback и не расширять packet.
