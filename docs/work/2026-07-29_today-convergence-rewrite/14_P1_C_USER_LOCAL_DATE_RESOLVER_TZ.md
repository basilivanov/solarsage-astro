# P1-C — Pure user local-date resolver

Phase / Wave: `today-convergence-2 / P1 (W2-S0)`

Modules: new `M-USER-LOCAL-DATE` service and its owned unit tests.

## Goal

Создать один чистый backend helper `resolve_user_local_date(user, now)`, который
вычисляет текущую календарную дату пользователя по каноническому приоритету:

```text
profile.current_tz → profile.birth_tz → UTC
```

Этот packet создаёт и доказывает resolver отдельно. Переключение Day и Calendar
должно произойти атомарно в следующем packet; здесь нельзя частично менять
consumer call graph.

## Exact write scope

- `apps/api/app/services/user_local_date.py` — new;
- `apps/api/tests/test_user_local_date.py` — new;
- этот packet-документ.

## Frozen / out of scope

- `apps/api/app/api/day.py`, Calendar, drilldown, Yesterday, check-in и pregen;
- Today/Calendar wire contracts и generated artifacts;
- profile schema/model/migration;
- birth-time control-grid logic;
- любое изменение frozen W1 canon;
- commits and push.

## Required contract

- public entrypoint имеет точное имя `resolve_user_local_date(user, now)`;
- `now` обязан быть timezone-aware; naive datetime отвергается стабильной
  domain-ошибкой, а не трактуется как server local time;
- непустой `current_tz` имеет приоритет над `birth_tz`;
- при отсутствующем `current_tz` используется `birth_tz`;
- при отсутствии обоих используется `UTC`;
- выбранная непустая, но невалидная IANA timezone не замалчивается UTC-fallback:
  helper поднимает безопасную стабильную domain-ошибку без profile values;
- conversion выполняется через stdlib `zoneinfo`; внешние зависимости не нужны;
- функция не читает системные часы сама, не мутирует user/profile и не логирует
  персональные значения;
- новый файл полностью размечен GRACE: AI_HEADER, MODULE_CONTRACT, MODULE_MAP,
  START_BLOCK, FUNCTION_CONTRACT, `owned_tests`, честные `emitted_logs: none`.

## Required tests

- west of UTC: один UTC instant остаётся предыдущей локальной датой;
- east of UTC: один UTC instant становится следующей локальной датой;
- `current_tz` реально побеждает конфликтующий `birth_tz`;
- отсутствие current использует birth;
- отсутствие обоих использует UTC;
- DST boundary на IANA-зоне доказывается aware UTC instants по обе стороны
  локальной полуночи в дату перехода;
- aware datetime с не-UTC offset корректно нормализуется;
- naive `now` fail-closed;
- invalid selected timezone fail-closed и не раскрывает timezone/profile в
  тексте исключения.

Тест `today` против явной ISO-даты остаётся обязательным acceptance gate
следующего consumer packet: этот pure resolver не парсит HTTP path.

## Verification

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_user_local_date.py -q
/opt/solarsage-astro/apps/api/.venv/bin/ruff check app/services/user_local_date.py tests/test_user_local_date.py
cd ../..
python3 scripts/grace_lint.py apps/api/app --quiet
python3 scripts/check_logging_guardrails.py
git diff --check
```

## Expected evidence

- все перечисленные timezone/DST/failure cases PASS;
- exact diff состоит только из двух новых code/test-файлов и этого документа;
- никаких новых dependency или wire/generated diffs;
- coder не коммитит и не пушит.

## Escalation

Если для helper требуется менять ORM, schema, endpoint или трактовать invalid
timezone как UTC, остановиться и доложить reviewer: это изменение контракта, а
не расширение этого packet.
