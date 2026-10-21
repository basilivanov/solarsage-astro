# Известные баги / технический долг

> Часть operative canon репозитория (вместе с AGENTS.md и `docs/agents/*`).
> Извлечено из AGENTS.md 2026-10-22; AGENTS.md содержит резюме и ссылку на этот файл.
> Закрытые строки удаляются только после фактической приёмки фикса.

| # | Баг | Где | Суть |
|---|-----|-----|------|
| ~~1~~ | ~~`Transit_` / `Natal_` в UI~~ | FIXED 2026-08-01 (27c18f71) | Стриппинг + локализация в `today_service.py`/`astro_utils.strip_prefix`, плюс fail-closed `narrative_sanitizer.py` на всех narrative-ответах. |
| 2 | SolarSage не отдаёт `planet.house` | `normalization_service.py:60` — `_planets_in_houses()` | SolarSage возвращает `houses: [{number, cusp}]` отдельно от планет. `NormalizationService` вынужден вручную маппить `planet.longitude → house` через `_find_house()`. Это лишняя работа на стороне API. **Fix:** добавить в SolarSage выдачу `planet.house` сразу при расчёте транзитов и натала. |
