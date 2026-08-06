# 65 — Narrative: заземление summary на драйвер + fail-closed валидация (реализация ТЗ 57)

Ты — coder. Skill coder-loop использовать НЕЛЬЗЯ. Ничего не коммить — коммит делает ревьюер.

Норматив: `docs/work/2026-08-03_today-ux-round2/00_MASTER_TZ.md` §57 (approved: делаем оба фикса). Принцип владельца: не шаблоны — персонально, но заземлённо на детерминированные факты.

## Фактура (проверено ревьюером)

`apps/api/app/services/today_narrative_service.py` строит prompt input, где по каждому блоку (convergence/mainEvent/impulse) есть только `kind/sphere/polarity/eventTime` (~строки 600-640). Промпт просит «формулируй текст claim только общими словами по kind, sphere и polarity». Итог: LLM сочиняет generic, уезжает в чужую сферу/полярность, и валидация это не ловит. Живой пример владельца: импульс «Меркурий в гармонии с твоим Ураном» (Документы, supportive) получил summary «Встречи в сфере отношений могут стать более напряжёнными».

Детерминированные title событий уже есть (55B): `apps/api/app/services/today_convergence_titles.py` → `build_today_convergence_event_title` (None, если честный title построить нельзя). Темы планет есть в каноне `grace/canon/today_convergence_themes.v1.yml` (`target_planet_themes`).

## 1. Grounding промпта

- В prompt input каждого блока добавить по каждому событию: `title` (если удалось построить, иначе поле отсутствует) и краткие `driverThemes` — человеческие темы планет из канона (напр. Меркурий — мышление/документы/контакты; взять из `target_planet_themes`/существующих словарей, не выдумывать новых сущностей).
- Обновить текст промпта: summary обязан опираться на title/темы драйвера и кратко пояснять, что это за фактор и почему он про эту сферу; по-прежнему ≤220 chars, без часов/дат/окон, без категоричных предсказаний. Сохранить запрет служебных имён (Transit_/Natal_/Planet/«M, Mars»).

## 2. Fail-closed валидация соответствия

Расширить `apps/api/app/services/narrative_sanitizer.py` (или соседний валидатор нарративов — выбрать по месту, сохранив GRACE-контракты):

- Словарь сфер: 12 канонических labels + очевидные формы («отношени», «документ», «деньг», «работ», «здоров», «учёб/учеб», «поезд», «творч», «покуп», «спорт», «общен», «решен»). Если summary блока со сферой X содержит словарь ДРУГОЙ сферы Y (Y ≠ X, с учётом допустимых пересечений: documents↔communication/study, money↔shopping, health↔sport, relationships↔decisions?) — reject. Пересечения зафиксировать явной картой «родственных» сфер, чтобы не резать легитимные связи (secondarySphere у convergence допустим).
- Polarity-антонимы: при polarity=supportive reject слова «напряж*», «конфликт*», «обостр*»; при tense reject «легко/лёгк*», «гармонич*» — минимальный консервативный список, только явные противоречия.
- Reject-поведение как в существующем контуре: одна регенерация, затем claim=null (honest pending), без показа сырья. Никаких исключений наружу из-за санитайзера — только события логов по существующему registry (новые события сначала в registry/contract).
- Покрыть тестами: позитив (валидный текст проходит), сфера-mismatch (пример владельца), polarity-антоним, родственные сферы пропускаются.

## 3. Regression-защита примера владельца

Тест: блок impulse sphere=documents polarity=supportive с title «Меркурий в гармонии с твоим Ураном» → сгенерированный/проверенный summary не содержит «отношени»/«напряж»; ответ «Встречи в сфере отношений могут стать более напряжёнными» — reject.

## Скоуп

Только backend: `apps/api/app/services/today_narrative_service.py`, `narrative_sanitizer.py` (+возможно новый соседний модуль валидации), `apps/api/tests/*`, при необходимости `apps/api/app/core/logging_events.py` (новые события). НЕ трогать frontend, контракты OpenAPI (вход/выход endpoint'ов не меняются), канон YAML.

## Verification (обязательно, показать вывод)

- `cd apps/api && source /opt/solarsage-astro/apps/api/.venv/bin/activate && python -m pytest tests/ -q -m "not integration and not benchmark" 2>&1 | tail -3`
- `python3 scripts/check_logging_guardrails.py | tail -2`
- `git diff --check`
