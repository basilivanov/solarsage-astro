# Синастрия — пакет артефактов

Все материалы фичи хранятся в одной feature-ветке, но разделены по роли:

| Artifact | Path | Role |
|---|---|---|
| Design/LLM master | [`00_DESIGN_AND_LLM_CONTRACT.md`](./00_DESIGN_AND_LLM_CONTRACT.md) | UX, язык, safety boundaries |
| Implementation TZ | [`01_TZ_REACT_ADAPTATION.md`](./01_TZ_REACT_ADAPTATION.md) | API/DB/frontend/ops contract |
| Technical pre-mortem | [`02_TECHNICAL_PREMORTEM.md`](./02_TECHNICAL_PREMORTEM.md) | risks, gates, rollback, verdict |
| Scoring appendix | [`03_SCORING_AND_TONE_CONTRACT.md`](./03_SCORING_AND_TONE_CONTRACT.md) | deterministic numerical canon |
| HTML prototype | [`public/prototypes/synastry/index.html`](../../../public/prototypes/synastry/index.html) | visual/interaction reference |

Статус: ТЗ готово к реализации только через merge gates из раздела 9 `01`.
Production activation отдельно заблокирована staged rollout и smoke gates.

Prototype не является production dependency: React/API/tests не импортируют
его файлы и не используют demo data в runtime.
