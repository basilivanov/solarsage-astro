# 53 — TODAY SERVICE COVERAGE RECOVERY TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(первый), cwd `/tmp/solarsage-convergence-impl`, ветка `work/today-convergence-2`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру.

## 1. Packet title

Coverage recovery: `apps/api/app/services/today_service.py` обратно к
fail-under=88 (сейчас 82.75) точечными unit-тестами на ЖИВОЙ сервисный код
legacy TodayService. HTTP wire-контракт НЕ восстанавливаем.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / CI gate recovery (coverage floor не понижаем,
06 §2.2). Legacy TodayService удаляется только в W9 — до тех пор его
критический coverage floor обязан стоять.

## 3. Modules

- Tests: `apps/api/tests/test_today_service_cache_unit.py` (новый) и/или
  расширение существующих test_today_service* файлов (смотри что уже есть).

## 4. Goal

`python -m coverage report --include="apps/api/app/services/today_service.py"
--fail-under=88` проходит после прогона полного backend suite. Недопокрытые
строки по CI report: 230, 281, 384, 531-550, 596, 607->606, 615, 617,
640-641, 659, 685->692, 695, 736-765, 926, 931, 987, 992->993, 1002, 1013,
1038->1041, 1078->1080, 1130, 1142-1149, 1155, 1157, 1181->1184, 1192-1194,
1256-1257, 1335-1342.

## 5. Контекст (прочитать перед кодированием)

- `apps/api/app/services/today_service.py` — legacy сервис (НЕ менять).
  Живые публичные пути после P4-D2: `invalidate_cache` (используется
  profile API), versioned cache identity/reads/writes
  (`expected_cache_identity`, `_get_cached_payload`, `_cache_payload`),
  `_build_preview_payload`, `compute_profile_hash` цепочки.
- Существующие тесты сервиса: `apps/api/tests/test_today_v2_payload.py`,
  `test_wave3_day_pipeline_reuse.py`, `test_today_service_v2_dual_run.py` и
  др. — НЕ ломать.
- Команда замера:
  `cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/ -q -m "not integration and not benchmark" --cov=app --cov-branch \
  --cov-report= && /opt/solarsage-astro/apps/api/.venv/bin/python -m \
  coverage report --include="apps/api/app/services/today_service.py" \
  --fail-under=88`

## 6. Exact write scope

- `apps/api/tests/test_today_service_cache_unit.py` (новый)
- Допустимо расширить `apps/api/tests/test_today_v2_payload.py` — только
  новыми test functions, без изменения существующих assertions.
- НИЧЕГО больше (production код не трогать).

## 7. Frozen / Out of scope

- НЕ менять: today_service.py и любой production код; не восстанавливать
  удалённые HTTP-тесты и legacy wire expectations.
- НЕ снижать пороги и не трогать ci.yml.

## 8. Требования к тестам

- Unit-уровень (mock db/sidecar/LLM по существующим паттернам
  test_today_v2_payload.py); цель — закрыть живые недопокрытые блоки
  (cache identity mismatch/miss/hit ветки, preview payload builder,
  invalidate_cache, versioned cache-key ветки, error/fallback ветки).
- Тесты фиксируют ТЕКУЩЕЕ поведение живого кода (characterization), не
  старый HTTP-контракт.
- GRACE-разметка тестового модуля (MODULE_CONTRACT/MAP, owned_tests: self).

## 9. Verification

```bash
cd /tmp/solarsage-convergence-impl/apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_service_cache_unit.py -q -p no:cacheprovider
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" -p no:cacheprovider 2>&1 | tail -2
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ -q \
  -m "not integration and not benchmark" --cov=app --cov-branch --cov-report= \
  2>&1 | tail -1
/opt/solarsage-astro/apps/api/.venv/bin/python -m coverage report \
  --include="apps/api/app/services/today_service.py" --fail-under=88
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  tests/test_today_service_cache_unit.py
cd /tmp/solarsage-convergence-impl && \
  python3 scripts/grace_lint.py apps/api/tests/test_today_service_cache_unit.py
```

## 10. Expected evidence

- Вывод всех команд §9; итоговый процент today_service (>=88); список
  закрытых блоков (по строкам из §4).

## 11. Escalation rule

Если для 88 нужны тесты на мёртвый/удалённый код или правки production —
СТОП, доложить с фактическим %.

## 12. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
