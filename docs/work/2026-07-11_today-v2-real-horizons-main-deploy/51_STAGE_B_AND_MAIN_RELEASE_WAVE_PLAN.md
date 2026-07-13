# Stage B + Main Release Execution Plan — wave boundaries and authority

Дата: 2026-07-12
Ветка реализации: `preview/solarsage-v2-human-first-navigator-ux`
Принятый Stage A2 HEAD/origin: `f0d8bef19ec4f0806039cf44a173a22bb4f60a1c`
Masters:

- `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md`
- `90_MAIN_RELEASE_DEPLOY_TZ.md`

Статус: **ACTIVE EXECUTION PLAN**.

## 0. Роли и протокол

- Architect пишет каждое wave-ТЗ, принимает diff и самостоятельно повторяет
  gates.
- Coder работает только в tmux `astro:0.0`.
- Полное задание всегда хранится в `docs/work`; в tmux передаётся только path и
  короткая команда прочитать его полностью.
- Субагенты и delegated coding agents не используются.
- Пока coder работает, architect проверяет состояние не чаще одного раза в три
  минуты.
- Commit/push каждой волны запрещён до отдельного acceptance и commit/push ТЗ.
- `main`, systemd, nginx, production env и canonical runtime не меняются до
  принятой финальной release wave.

Unrelated paths всегда сохраняются:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 1. Authority order

При конфликте требований использовать порядок:

1. актуальный root `AGENTS.md`;
2. этот execution plan;
3. wave-specific ТЗ;
4. master `50` для продукта;
5. master `90` для release;
6. более ранние preview/fixture docs только как historical reference.

Wave-specific ТЗ может сужать scope, но не ослаблять product safety,
provenance, real-data или release requirements masters.

## 2. Stage B decomposition

### B1 — additive public contract + consumer boundary

Цель:

- добавить backend-owned public horizon contract;
- доказать validators и additive compatibility;
- научить frontend предпочитать `v2.horizons` и сохранять legacy fallback при
  `null/absent`;
- показать contract-valid backend-shaped test fixture;
- production backend пока не заполняет horizons.

Не входит:

- selection canon;
- calculation/selection/fact pack;
- TodayService population;
- LLM;
- real non-fixture acceptance URL.

Owning ТЗ: `52_STAGE_B1_HORIZON_CONTRACT_CONSUMER_TZ.md`.

Expected commit:

```text
feat(today): add grounded three-horizon response contract
```

### B2 — deterministic timing, selection, facts and guidance

Цель:

- typed canon files and loaders;
- horizon timing/classification;
- bounded deterministic coherent triple selection;
- product-sphere mapping;
- personal fact pack from natal/scoring/profile allowlist;
- deterministic guidance and claim validation;
- coverage corpus and performance proof.

На выходе сервисы строят complete `TodayV2HorizonsBlock` без LLM, но
production Today flow ещё не обязан его включать.

Не входит:

- TodayService/SemanticV2 integration;
- cache identity bump;
- LLM refinement;
- production frontend preview.

Expected commit:

```text
feat(today): select coherent personal horizons deterministically
```

### B3 — real API population, cache, logs and optional refinement

Цель:

- integrate B2 into existing Today objects without duplicate sidecar/natal/
  scoring calls;
- populate real `v2.horizons`;
- cache/content/canon identity;
- registered structured logs;
- optional constrained LLM rewrite with atomic validation/fallback;
- real API payload and redacted provenance proof.

На выходе API отдаёт реальные backend horizons; frontend B1 consumer уже может
их показать, но B4 делает production-quality UI и real preview acceptance.

Expected commit:

```text
feat(today): populate grounded horizons with safe refinement
```

### B4 — production frontend and real preview 3003

Цель:

- завершить human-first карточки, actions/avoid, strength/risk,
  manifestations and technique disclosures;
- clickable links to 12-sphere navigator;
- visible tone/timing semantic contract;
- mobile/desktop/a11y visual proof;
- real API/dev-auth URL on 3003 without fixture query or interception.

Expected commit:

```text
feat(today): render backend-owned personal horizons
```

### B5 — stabilization and release candidate

Цель:

- закрыть все known baseline failures, связанные с release contract;
- full unit/backend/frontend/Playwright/guardrail matrix;
- real Telegram HMAC E2E without interception;
- performance/security/log/PII audit;
- clean pushed feature branch and written `READY_STAGE_B_FOR_MAIN_RELEASE`.

Expected commit(s):

```text
fix(today): stabilize real horizon pipeline
test(today): prove real horizon pipeline end to end
```

Количество commits определяется acceptance, но каждый должен иметь отдельный
exact path audit.

## 3. Cross-wave invariants

### 3.1 Contract ownership

```text
Pydantic API models
  -> generated OpenAPI
  -> generated TypeScript
  -> generated Zod
  -> frontend public barrels
```

Запрещено вручную объявлять raw horizon wire shape в frontend.

### 3.2 Real-data ownership

- Sidecar owns factual astrology/timing.
- API owns selection, coherence, personal facts, language, actions and tone.
- Frontend owns layout/interactions only.
- Fixture is test/dev evidence, not production runtime source.

### 3.3 Grounding

Каждый personal claim/action имеет typed provenance. Unknown life context всегда
conditional. Нельзя выдумывать profession, partner, debt, diagnosis, firing,
move, deal or already-happened event.

### 3.4 Compatibility

Каждая public contract wave:

```text
pnpm contracts:sync
compatibility additive/no-change
breakingChanges = 0
overrideUsed = false
generated diff accepted with owning Pydantic change only
```

### 3.5 Baseline discipline

До B5 known API failures можно сохранять только если wave ТЗ explicitly
разрешает exact baseline. B5 release candidate требует full green: baseline-red
нельзя переносить в `main` release acceptance.

### 3.6 No premature production mutations

До final release запрещены:

- `git switch main`;
- push `main`;
- systemctl restart/reload;
- production env edits;
- `.next-prod` swap;
- manual uvicorn;
- nginx edits;
- production evidence artifacts.

## 4. Review/commit lifecycle per Stage B wave

Каждая B1–B5 проходит одинаковый lifecycle:

```text
architect writes wave TZ
  -> coder implements without commit
  -> coder callback
  -> architect reads full diff and reruns gates
  -> correction docs/loops if needed
  -> architect acceptance doc
  -> architect exact commit/push TZ
  -> coder exact commit/push
  -> architect verifies origin SHA and clean tracked tree
  -> next wave TZ
```

Нельзя объединять непринятые волны в один commit.

## 5. Main release decomposition

Production release выполняется после B5 acceptance как одна controlled release
операция с четырьмя внутренними phases. Между phases architect проверяет gate;
coder не останавливает release в потенциально несогласованном состоянии без
явного blocker/rollback callback.

### R0 — read-only release preflight

- fetch and SHA proof;
- feature/main ancestry and diff audit;
- full release tests on feature;
- read-only systemd/ports/health/env-key presence;
- build/install plan and rollback identifiers;
- no branch switch, env edit, restart or build swap.

Gate: `READY_RELEASE_PREFLIGHT` accepted by architect.

### R1 — merge main + shared wheel + isolated candidate build

- merge feature into main with non-ff merge commit;
- push main only after local post-merge checks;
- build one `solarsage-contracts` wheel from accepted main SHA;
- record wheel SHA-256;
- install same wheel into sidecar/API venvs and `pip check`;
- scoped flags backup/edit if required;
- isolated Next candidate build;
- candidate smoke on loopback 3010;
- production services still serving old processes/build until R2.

Gate: candidate healthy, rollback artifacts ready, main/origin SHA equal.

### R2 — atomic production activation

- preserve old `.next-prod` as rollback dist;
- atomic candidate rename;
- restart sidecar -> API -> frontend with bounded health waits;
- no nginx reload unless config changed and `nginx -t` passes;
- immediate rollback on health failure.

Gate: all canonical services/ports healthy.

### R3 — authenticated production proof and evidence

- real Telegram HMAC payload;
- provenance/timing/source validation;
- real browser E2E against public host without route interception/fixture;
- sanitized screenshot/network/payload/release report;
- log error/PII audit;
- optional dedicated safe evidence commit;
- final rollback command and artifact retention proof.

Only after R3 architect may mark the full goal complete.

## 6. Release stop/rollback rules

Before main merge, any failed gate means stop with no production mutation.

After main merge but before activation, failure means:

- do not restart production;
- do not swap `.next-prod`;
- fix via normal follow-up commit on main only after architect review, or revert
  merge if release is abandoned.

After activation begins, any canonical health/auth/wire/render failure triggers
the rollback procedure from `90_MAIN_RELEASE_DEPLOY_TZ.md`; never use reset or
force-push.

## 7. Definition of completion

The program is complete only after authoritative evidence proves all of:

```text
real timing -> coherent backend triple -> grounded actions/provenance
generated wire -> backend-owned frontend render -> 12-sphere navigation
full green tests/build/guardrails/performance
accepted commits in origin/main
same shared wheel in both Python venvs
canonical systemd deploy
real Telegram HMAC production E2E
safe rollback artifacts and no secret/PII leakage
```

Feature preview, fixture screenshots, focused tests or pushed feature branch are
not completion by themselves.
