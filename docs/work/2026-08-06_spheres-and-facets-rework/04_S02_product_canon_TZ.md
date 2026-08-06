# S2 TZ — product_spheres canon + strict loader/resolver

## packet title
S2-product-canon-resolver

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-CONVERGENCE-CANON (`apps/api/app/services/today_convergence_canon.py`)

## goal
Создать `grace/canon/product_spheres.v1.yml` как единственный источник 12
продуктовых сфер и facets, переключить `today_convergence.v1.yml` sphere_projection
на него (fan-out удалён) и реализовать один deterministic resolver
`(sphere, facet|None)` в текущем canon-модуле. Юнит/групп-проджекшн — отдельный
срез S3; здесь только канон, загрузчик, resolver и его тесты.

## Таксономия
Источник истины по содержимому — мастер-ТЗ §3 (12 ключей и порядок) и §4
(facets: ключ, русский label, дома, нужный контекст) и §5 (приоритеты и запреты).
Ключ `finance` (не `money`); `decisions`/`shopping` отсутствуют.

## exact write scope
- `grace/canon/product_spheres.v1.yml` (новый)
- `grace/canon/today_convergence.v1.yml` (секция sphere_projection)
- `apps/api/app/services/today_convergence_canon.py`
- `apps/api/tests/test_today_convergence_canon.py`

## frozen / out-of-scope
- `grace/canon/spheres.v1.yml` (технический scoring-канон — НЕ трогать)
- `grace/canon/today_convergence_themes.v1.yml`
- `apps/api/app/services/today_convergence_units.py`, `today_convergence_groups.py`,
  `today_convergence_selection.py`, `today_convergence_tone.py` (S3/S4)
- frontend, schemas, fixtures

## must-preserve invariants
- significance/eligibility/rare anchors/direct grouping/hero C1/birth-time/tone
  секции `today_convergence.v1.yml` — без изменений (diff должен касаться только
  sphere_projection и связанных проверок).
- `compute_today_convergence_canon_hash` меняет значение — ок; структуру функции
  можно расширить на product_spheres.v1.yml (он должен входить в hash).
- Существующий fail-closed характер loader'а (`TodayConvergenceCanonError`) сохранить.
- `spheres.v1.yml` продолжает грузиться прежними потребителями (canon_service).

## Требования

1. `product_spheres.v1.yml`: schema_version, status, canonical order (12 keys),
   per sphere: key, ru title/description, facets[] (key, label, houses[],
   required_context?, modifiers planets[]), priority rules, запрет planet-only
   для узких facets. Структура — на твоё усмотрение, но self-describing.
2. `today_convergence.v1.yml` `sphere_projection`: canonical_order = новые 12;
   удалить `technical_to_product`, `technical_alias_to_product`, `planet_to_product`,
   `planet_sphere_limits`, secondary; ссылка на product_spheres.v1.yml как источник
   проекции; правило one group → one sphere → one facet|null. Статус канона
   (`frozen_w1`) либо сохранить, либо синхронно обновить проверку в loader'е —
   YAML и loader не должны расходиться.
3. `today_convergence_canon.py`:
   - загрузка и строгая валидация product_spheres.v1.yml (ровно 12 keys в порядке,
     unique facets внутри sphere, houses 1..12, неизвестные ключи/ссылки — fail-closed);
   - удалить helpers старого fan-out (`map_factor_to_product_spheres` и пр.);
   - добавить ОДИН resolver: по данным {house, technical_spheres, context/theme keys,
     source/target planets} возвращает `(sphere, facet|None)` либо `None` (unresolved);
     приоритет: house → technical_spheres → явный context → планеты только как
     tie-break; planet-only узкий facet запрещён; неизвестное → None (НЕ fallback work);
     детерминизм при перестановке входов.
4. Тесты `test_today_convergence_canon.py` переписать под новую модель (мастер-ТЗ §9.1):
   12 keys/порядок, нет decisions/shopping, есть home_family/friends_goals, facets
   уникальны, houses валидны, fail-closed на неизвестном, planet-only не создаёт
   узкий facet, дома из §4 маршрутизируются как ожидается (2→finance/personal_money,
   8 без контекста ≠ obligations, Уран без 3/9 ≠ travel, Нептун/Уран без 5 ≠ creativity).

## verification commands
```bash
cd /opt/solarsage-astro/apps/api && .venv/bin/python -m pytest tests/test_today_convergence_canon.py -q
```
Плюс `python3 scripts/grace_lint.py apps/api/app` → PASS.

## expected evidence
- diff; вывод pytest; краткий пример resolver-вызова (вход → выход) для
  house=2 и для Uranus-only случая.

## escalation rule
Если resolver'у нужны поля, которых нет в текущих unit/fact структурах — стоп,
доложить (это S3 scope), новый packet.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
