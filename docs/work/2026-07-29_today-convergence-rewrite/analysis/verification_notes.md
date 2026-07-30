# Verification notes (redirect tasks T1–T4, 2026-07-29)

Этот файл фиксирует результаты, которые иначе жили бы только в сообщениях агента.
Всё диагностическое, не фриз. Ограничения соблюдены: БД read-only, без LLM, без секретов/дат рождения в выводе.

## T1 — canon ↔ harness alignment

- Правила: `hero_confirmation_fast_allowed: False`, `hero_target_types: ("natal_planet", "angle")` в `ablation_harness.py` (функция `_hero_ok`); medium/convergence не затронуты.
- Результат (пересчитано дважды, в т.ч. после resume): **hero = 8/81** — 06-15, 06-24, 07-01, 07-03, 07-08, 07-21, 07-23, 08-03; states: hero 8 / convergence 71 / single 2.
- Выпавшие дни подтверждены по составу групп: 06-04 (единственный свидетель MOON), 06-17 (lot-таргет + MOON-свидетель).
- Артефакт: `ablation_t1_canon_align.json` (конфиг, список дней, детали hero-групп).

## T2 — engine sect fix (apps/solarsage)

- Рабочее дерево уже содержало чужой незакоммиченный W2-чаинсет с геометрической сектой; мои изменения поверх: `sect_polar_condition` ("polar_day"/"polar_night"/None) в `NatalCalculationContext` + debug firdar major/minor (`solarsage/services/activation_builder.py`); тесты (a)–(d) в `tests/test_geometric_sect.py`.
- Сьют: **240 passed, 1 failed**; единственный фейл `test_solar_return...same_year_after` — пре-существующий 1-секундный флейк (падает и на чистом HEAD, проверено git stash).
- Live A/B :18091 vs :18099 по карте владельца (время не печаталось): старый — немонотонные флипы секты (firdar SUN↔SATURN 12:00↔13:00); новый — стабильно по высоте (12:00 +7.97° day, 13:00 +8.01° day, 16:00 +0.10° day, 17:59 −9.83° night). Секта в 12:00 изменилась (night→day) → фикс меняет firdar-лорды.
- **Блокер для прод-выката**: `CALCULATION_VERSION="ss-calc-1.2.0"` живёт в `packages/py-contracts/solarsage_contracts/versions.py` (вне разрешённой зоны записи). Нужен бамп одной строкой, иначе кэши natal/activation не инвалидируются по новой секте.
- Фиксированный сайдкар standalone на `127.0.0.1:18099` (uvicorn из venv сайдкара). Перезапуск: `cd /opt/solarsage-astro/apps/solarsage && PYTHONPATH=/opt/solarsage-astro/apps/solarsage venv/bin/uvicorn solarsage.app:app --host 127.0.0.1 --port 18099`.

## T3 — corpus runner

- `analysis/corpus_runner.py`: chart-day чекпоинты (atomic), resume (проверено 4/4 skipped), шардирование `index % workers` (+`--shards/--shard`), per-worker httpx-клиент на :18099, `failures.jsonl`, агрегация (states, hero rate, impulses, tense-серии по выбранным юнитам, hero-сферы, латентности).
- Дубликат: `corpus_replay.py` (in-process, без HTTP) — перед фризом выбрать один путь.

## T4 — benchmark

- `analysis/corpus_benchmark.md` (RU) + `corpus_benchmark.json`: 5 карт × 30 дней × 3 режима = 450 chart-day, 0 ошибок; wall 254.9/249.7/262.6с (w1/w2/w4); sidecar 0.94–0.98 ядра уже при 1 воркере → scaling eff 0.51/0.24; chart-day mean 0.561с, median 0.451с, p90 1.103с; проекция корпуса ≈ 45ч на 1 сайдкар (4 реплики ≈ 11–12ч).
