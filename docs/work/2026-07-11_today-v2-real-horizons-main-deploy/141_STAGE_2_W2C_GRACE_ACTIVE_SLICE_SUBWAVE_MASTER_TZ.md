# Stage 2.W2C — GRACE active-slice migration subwave master

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`d50f0268efe6c5c9ea88e7c6bc1cc12f85fdfc6e`
Parent: `127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`
Evidence: `/tmp/stage2-w2b2b-accepted-guardrails-frontend.log`

Статус: **W2C EXECUTION MASTER — COMMENT-ONLY CONTRACT MIGRATION, ONE SUBWAVE AT A TIME**

## 1. Exact accepted baseline

Frontend source lint and typecheck are now green. The only
`guardrails:frontend` blocker is the GRACE marker gate:

```text
violations          49
failing paths       41
already-green paths  6
checked paths       47
```

The 49 violations decompose exactly as:

```text
missing module maps       41
missing module contracts   5
missing AI headers          3
```

The three missing-header paths are also among the five missing-contract paths.
No block-pairing, file-size or function-size violation exists.

## 2. Exact 41-path failing inventory

### W2C-1 — app pages: 14 paths / 17 violations

```text
app/(grace)/calendar/page.tsx
app/(grace)/chat/page.tsx
app/(grace)/checkin/page.tsx
app/(grace)/debug/page.tsx
app/(grace)/onboarding/page.tsx
app/(grace)/page.tsx
app/(grace)/profile/page.tsx
app/(grace)/readings/horary/[id]/page.tsx
app/(grace)/readings/horary/page.tsx
app/(grace)/readings/natal/[id]/page.tsx
app/(grace)/readings/natal/generating/page.tsx
app/(grace)/readings/natal/page.tsx
app/(grace)/readings/page.tsx
app/(grace)/today/page.tsx
```

### W2C-2 — GRACE components: 11 paths / 11 violations

```text
components/grace/CalendarGrid.tsx
components/grace/CalendarMonth.tsx
components/grace/DayNavigation.tsx
components/grace/ErrorBoundary.tsx
components/grace/LoadingSpinner.tsx
components/grace/LockedDay.tsx
components/grace/Reading.tsx
components/grace/ReadingCard.tsx
components/grace/TodayScreen.tsx
components/grace/TopFlags.tsx
components/grace/WeekStrip.tsx
```

### W2C-3 — API facades: 13 paths / 18 violations

```text
lib/api/access.ts
lib/api/calendar.ts
lib/api/chat.ts
lib/api/checkin.ts
lib/api/cities.ts
lib/api/config.ts
lib/api/dev-auth-guard.ts
lib/api/horary.ts
lib/api/natal.ts
lib/api/profile-meta.ts
lib/api/profile.ts
lib/api/readings.ts
lib/api/today.ts
```

### W2C-4 — GRACE library: 3 paths / 3 violations

```text
lib/grace/hooks/useCalendar.ts
lib/grace/hooks/useDay.ts
lib/grace/index.ts
```

Total: 14 + 11 + 13 + 3 = 41 paths; 17 + 11 + 18 + 3 = 49 violations.

## 3. Migration contract

Every failing file receives or consolidates one canonical pre-runtime preamble:

```text
AI_HEADER banner in first 30 lines
START_MODULE_CONTRACT:<unique id> / matching END
START_MODULE_MAP:<same unique id> / matching END
```

The content must be truthful, not merely gate-shaped:

- `purpose` names the actual caller/use case;
- `owns` contains the exact path;
- `inputs` describes route props, hooks, function arguments or API input;
- `outputs` describes rendered UI or return type;
- `dependencies` lists material local/framework/API dependencies;
- `side_effects` identifies navigation, state, fetch, storage or none;
- `emitted_logs` lists exact registry event names, or `none`;
- `invariants` names observable behavior that must remain stable;
- `failure_policy` describes real delegation/error/redirect behavior;
- map `public_entrypoints` lists actual exports;
- map `semantic_blocks` names conceptual code regions without requiring new
  START_BLOCK comments;
- map `owned_tests` lists direct tests when present, otherwise `none direct`.

Canonical IDs are unique and path-derived. Module contract and map IDs within
one file must match exactly.

Existing generic or incorrect preambles may be replaced in the authorized
file. Redundant legacy mini-headers may be removed. Existing truthful blocks,
function contracts and paired block markers must be preserved.

## 4. Hard non-functional invariant

W2C is comments only. For every subwave:

- no import/export/type/constant/function/JSX/string/selector/whitespace inside
  executable code may change;
- no formatter may rewrite the body;
- no runtime/config/dependency/test behavior change;
- no rule/paths manifest/linter change;
- comment-stripped source before and after must be equivalent;
- staged diff must contain only comment and adjacent blank-line changes in the
  exact authorized paths.

Do not add function contracts or START_BLOCK markers merely for decoration in
this migration. Preserve any already present; the owned blocker is the module
preamble.

## 5. Gate progression

Expected deterministic marker remainder:

```text
after W2C-1 app pages       32 violations / 27 failing paths
after W2C-2 components      21 violations / 16 failing paths
after W2C-3 API facades      3 violations /  3 failing paths
after W2C-4 GRACE library    0 violations /  0 failing paths
```

After W2C-4, full `pnpm guardrails:frontend` must pass including negative tests.

Each subwave receives independent architect review and a separate normal push
before the next one begins.

## 6. Global gates per subwave

At minimum:

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py <authorized paths>
pnpm lint
pnpm typecheck
bash scripts/grace/check-negative.sh
git diff --check
```

Run `pnpm guardrails:frontend` diagnostically until W2C-4; only the exact next
marker remainder may fail. No runtime operation or build is needed for
comment-only packets.

## 7. Frozen and runtime invariants

Never touch/stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Main, env, systemd and canonical build remain untouched. Ports
3003/8001/18092 remain absent.

## 8. Authorized next subwave

Only W2C-1 app pages is authorized next through its dedicated implementation
TZ. Components/API/lib-grace files remain read-only until their own documents.
