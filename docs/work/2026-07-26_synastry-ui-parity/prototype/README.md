# Synastry HTML prototype

Open `/prototypes/synastry/` after starting the project.

This directory is the visual/interaction reference only. Production React,
API and tests must not import files from `public/prototypes/synastry/`.

Implementation documents:

- [`00_DESIGN_AND_LLM_CONTRACT.md`](../../../docs/work/2026-07-25_synastry-prototype/00_DESIGN_AND_LLM_CONTRACT.md);
- [`01_TZ_REACT_ADAPTATION.md`](../../../docs/work/2026-07-25_synastry-prototype/01_TZ_REACT_ADAPTATION.md);
- [`02_TECHNICAL_PREMORTEM.md`](../../../docs/work/2026-07-25_synastry-prototype/02_TECHNICAL_PREMORTEM.md);
- [`03_SCORING_AND_TONE_CONTRACT.md`](../../../docs/work/2026-07-25_synastry-prototype/03_SCORING_AND_TONE_CONTRACT.md).

Structure:

- `base.html` — approved visual prototype with demo synastry data;
- `aspect-drilldown.css` — mobile sheet styles for detailed aspect explanations;
- `aspect-drilldown.js` — clickable aspect interpretation, real-life examples and repair actions;
- `partner-time.css` — unknown birth time state in the add-partner form;
- `partner-time.js` — disables exact time and exposes reduced calculation precision;
- `loader.js` — composes the base document and interaction modules;
- `index.html` — public entry point.

`app.js`, `data.js`, `scenarios.js`, `logic.js` and `detail.css` are retained
only as historical design material. `index.html` does not load them and the
React implementation must not copy from them.

Unknown partner birth time keeps planetary aspects available but disables partner houses and ASC, and marks the report as approximate.

The production React UI and API calculation are intentionally untouched.
