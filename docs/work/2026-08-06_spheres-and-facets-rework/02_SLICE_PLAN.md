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

Hotfixes и доработки после первой выкатки (каждый — свой NN-файл ТЗ):

| # | Срез | Scope (основное) | Приёмка |
|---|------|------------------|---------|
| S13 | Quiet selection hotfix | selection quiet-path | quiet-дни наполняются, tests |
| S14 | Day past-date boundary | day.py | прошедшие даты корректны, tests |
| S15 | Target house resolver | sidecar natal target house, resolver priority, anchor-centric projection | quiet-дни с событиями, tests, live на dev |
| S16 | Narrative personal v4 | today_narrative_service.py, day.py, pregen person-проброс, prompt v4, cap 2000 | person/period в промпте, 3-claim шаблон, tests, live регенерация |
| S17 | Sanitizer false positives | narrative_sanitizer.py: маска имён жребиев, окно отрицания для polarity-антонимов | live-кейсы «жребий Брака»/«снизить напряжение» не null; «разговоры в romance» остаётся null; tests |
| S18 | Selection dedup | today_convergence_selection.py: дедуп по (sphere, facet) и evidence-паре до cap-3, audit+1 поле | нет дублей карточек как 08-30, tests |
| S19 | Narrative grammar v5 | текст промпта: роды планет, падежи; prompt version → v5 | tests зелёные, live-eyeball грамматики |
| S20 | CosmicLoader restore | today-screen.tsx: ветка loading → CosmicLoader вместо серого скелетона | loading показывает фирменный лоадер, vitest зелёные, e2e контракт цел |

Правило: промежуточные состояния не выкатываются; на dev — только после S11.
