# План оптимизации CI/CD pipeline (обсуждено 2026-07-24)

## Диагноз

Deploy workflow дублирует проверки: `source-quality` гоняет полный `ci.yml` на уже зелёном SHA; фронт собирается 3 раза; docker-образы собираются последовательно. Гейты при этом полезные (за неделю поймали egress, V2-флаги, visual baseline) — не ампутировать, а откалибровать.

## Рабочие пункты (по приоритету)

1. **CI #1 — `source-quality` → green-check**: в `deploy-production.yml` заменить повторный прогон `ci.yml` на проверку через `gh api` (`/repos/{owner}/{repo}/commits/{sha}/check-runs`), что у SHA есть зелёный CI-ран. Нет/absent/red → фейл. Экономия ~4-5 мин на деплой, гарантия сохраняется.
2. **CI #2 — skip-инпуты**: `workflow_dispatch` inputs `skip_visual`, `skip_e2e` (boolean) для backend-only деплоев — осознанный выбор в момент деплоя. По умолчанию false (все гейты активны).
3. **CI #3 — matrix-сборка**: три docker-образа (api/sidecar/frontend) параллельно через strategy.matrix. Экономия ~2-3 мин.
4. **CI #4 — visual → nightly**: visual-regression baseline-сьют и полный параноидальный набор (full e2e, нагрузка) — nightly cron workflow. После стабилизации digest-пути (CI #1).

## Целевая модель (не спешить)

```text
PR:      affected unit/integration + малый smoke (когда появится PR-флоу)
main:    full CI + образы + release e2e
prod:    deploy проверенных digests + smoke
nightly: параноидальный полный набор
```

Affected-tests по контурам (frontend/api/sidecar/contracts/infra) — ОТЛОЖИТЬ до появления PR-флоу (сейчас соло-пуши в main смешанными батчами, анализ не окупается).

## Принципы

- В прод едет тот же артефакт, что прошёл проверки (digest), не пересобранный код.
- Гейты не удалять — делать дешёвыми/опциональными.
- После каждого пункта — ТЗ кодеру по нашему циклу, ревью, деплой.
