# Manifest

> Source of truth for the contents of `docs/`. Every `*.md` in this directory
> (except this file) MUST be listed below. The list is verified by
> `pnpm guardrails:docs` (`scripts/check_docs_manifest.py`). Every file must also carry a YAML
> front-matter block validated by `scripts/check_frontmatter.py`.

## Active

- `00_Обзор_продукта.md`
- `01_MVP_экраны_и_навигация.md`
- `02_Today_screen.md`
- `03_Почему_так_у_меня.md`
- `04_SolarSage_нормализация_скоринг_кеширование.md`
- `06_Натальная_карта_контракт_и_фронт.md`
- `07_Backend_architecture_draft.md`
- `08_Frontend_current_state_and_alignment.md`
- `09_Project_transfer_context.md`
- `10_GRACE_Project_Agent_Guide.md`
- `GRACE_CANON.md`
- `README_Структура_документации.md`
- `15_CI_без_GitHub_Actions_из_v0.md`

## Planned (target waves)

- `11_SolarSage_rewrite_TZ.md` — wave `W-SOLARSAGE-SVC`
- `12_Microcopy_dictionary_TZ.md` — wave `W-MICROCOPY`
- `13_Evening_checkin_TZ.md` — wave `W-EVENING`
- `14_SolarSage_scoring_rewrite_TZ.md` — wave `W-SOLARSAGE-ALGO`

## Superseded / stale

- `05_API_contracts_и_TodayPayload.md` — superseded by W-1.1B.
  Source of truth for payload shapes is now `apps/api/app/schemas/`
  and `packages/contracts/_generated.ts`.
- `DEPLOY.md` — stale (pre-W-1.0). References the old SolarSage CLI /
  systemd layout. Will be replaced by a W-DEPLOY packet.

## Related (outside docs/)

- Repo-level entry-point map: `../MANIFEST.md`
- Controller-packet index: `../grace/README.md`
- Project canon (XML): `../grace/canon/`
- TS contract barrel layout: `../packages/contracts/README.md`

## Module decisions

- `M-AUTH-TG` = Option A (opaque session cookie + server-side `sessions` table).
  See `grace/packets/W-1.2.md` `## Decision`.
