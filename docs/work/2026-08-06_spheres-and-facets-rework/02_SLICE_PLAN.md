# 02 — Slice plan: порядок реализации (coder-loop)

Каждый срез — отдельное локальное ТЗ `NN_SXX_..._TZ.md`, коммит делает ревьюер.
Зависимости учтены: контракты после backend-модели, frontend после контрактов.

| # | Срез | Scope (основное) | Приёмка |
|---|------|------------------|---------|
| S1 | Replay instrumentation + baseline | analysis/corpus_replay.py, generate_corpus_manifest.py | новые счётчики в отчёте, fingerprint расширен, baseline signatures сохранены |
| S2 | Product canon + resolver | grace/canon/product_spheres.v1.yml (новый), today_convergence.v1.yml, today_convergence_canon.py | 12 keys, resolver (sphere, facet\|null), fail-closed, canon tests |
| S3 | Units + group projection | today_convergence_units.py, today_convergence_groups.py | technical_spheres в unit, sphere/facet в group, identity не тронута, tests |
| S4 | Selection + wire | today_convergence_selection.py, schemas/today_convergence.py, projection | diversity gate убран, union cap/distinct удалены, schema_version 2, tests |
| S5 | Contracts + fixtures | pnpm contracts:generate, fixtures 01–18, barrel | generated обновлены, все fixtures на новых ключах, contract tests зелёные |
| S6 | Narrative + sanitizer | today_narrative_service.py, narrative_sanitizer.py | новые keys/patterns, capability rules, tests |
| S7 | Sphere context service | today_sphere_page_service.py (+генератор текстов), удаление today_sphere_drilldown.py | periodSynthesis/note, глитчи убраны, tests |
| S8 | Check-in migration | alembic + schemas/checkin.py + checkin-screen | money→finance, shopping→finance, decisions удаляется, tests |
| S9 | Frontend productization | удаление hero/sphere-pages, unified как единственная ветка, labels cleanup | тесты today-screen обновлены и зелёны |
| S10 | e2e + baselines | e2e specs, visual baselines | e2e зелёные |
| S11 | Replays | smoke + full corpus | gates из мастер-ТЗ §10.5, evidence report |
| S12 | Deploy dev | build .next-prod, restart units, smoke на dev | /api/health git_sha = HEAD |

Правило: промежуточные состояния не выкатываются; на dev — только после S11.
