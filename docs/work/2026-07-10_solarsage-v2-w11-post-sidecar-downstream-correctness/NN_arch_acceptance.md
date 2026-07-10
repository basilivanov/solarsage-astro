# W11 Architect Acceptance

Status: ACCEPTED
Date: 2026-07-10
Accepted implementation/evidence tip: `4182686`
Immutable final code/test commit: `2891217`
Base TZ commit: `87adec4`

## Decision

W11 now provides an independent and reproducible downstream correctness proof after the trusted sidecar `ActivationLayer` boundary. The audit independently recalculates mapping, contribution amounts, unique-family convergence, raw/cap math, and complete day-status breakdown; it rejects lost/extra/duplicate traces and invalid payload references; it writes the required artifacts; and the committed frontend fixture is schema-valid and rendered through the real `TodayScreen` path.

Live execution could not be completed because the deployed sidecar returns `404` for `/v1/activation-layer`. This is recorded as `NOT_RUN`, not represented as passing evidence. Synthetic and committed-path artifact replay modes both pass and the live mode implementation reconstructs real day signals through the normal transits, normalization, delta, and filter path.

## Accepted proof chain

```text
trusted ActivationLayer
  -> ActivationLayerService id multiset preservation
  -> independent activation-to-sphere mapping
  -> exact contribution formula trace
  -> exact convergence family/debug/contribution trace
  -> independent raw score and dominance cap trace
  -> independent full status breakdown
  -> payload V2 evidence/score/why id validation
  -> AdaptedTodayPayload fixture
  -> real TodayScreen / WhyExpanded / DevAuditDrawer tests
```

## Architect verification

### Backend W11 and scoring

```text
38 passed
```

### W10 regressions

```text
52 passed
```

### Frontend downstream fixture

```text
4 passed
```

### Audit modes

- Synthetic fixture: `status=ok`, `failure_count=0`.
- Committed-path artifact replay: `status=ok`, `failure_count=0`.
- V1 replay negative regression: passes by failing the invalid replay as required.
- Live audit: `NOT_RUN`, sidecar endpoint returned `404`.

### Contracts and static checks

- `pnpm contracts:generate`: passed with zero generated contract diff.
- `pnpm typecheck`: passed.
- `git diff --check 87adec4..4182686`: passed.
- `git show --check 4182686`: passed.
- Final working tree contains only the known pre-existing untracked local paths.

## Scope and delivery

- Remote CI: NOT_AVAILABLE.
- Push: NOT_ATTEMPTED.
- Deploy: NOT_ATTEMPTED.
- No production astrology or scoring weights changed.
- No rollout flags changed.

## Final verdict

Status: ACCEPTED
Accepted commit: `4182686`
Remote CI: NOT_AVAILABLE
Live downstream audit: NOT_RUN
Artifact replay audit: PASSED
Frontend fixture tests: PASSED
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED

Decision:
W11 proves that trusted sidecar activation ids and semantics are preserved, mapped, scored, capped, exposed in V2 payload evidence, and rendered by the frontend without downstream distortion; the only missing evidence is a live run blocked by the currently unavailable sidecar endpoint.
