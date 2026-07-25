# Synastry HTML prototype

Open `/prototypes/synastry/` after starting the project.

Structure:

- `base.html` — approved visual prototype with demo synastry data;
- `aspect-drilldown.css` — mobile sheet styles for detailed aspect explanations;
- `aspect-drilldown.js` — clickable aspect interpretation, real-life examples and repair actions;
- `partner-time.css` — unknown birth time state in the add-partner form;
- `partner-time.js` — disables exact time and exposes reduced calculation precision;
- `loader.js` — composes the base document and interaction modules;
- `index.html` — public entry point.

Unknown partner birth time keeps planetary aspects available but disables partner houses and ASC, and marks the report as approximate.

The production React UI and API calculation are intentionally untouched.
