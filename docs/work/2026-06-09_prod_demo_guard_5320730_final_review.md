# Final Review: W-PROD-DEMO-GUARD after rework

Date: 2026-06-09
Original reviewed commit: `a58d6b93c09cd65280125a9bad559be1dff9294c`
Rework commit: `5320730fd1cb53e880fe34677083bd4f696b7750`
Previous review: `docs/work/2026-06-09_prod_demo_guard_a58d6b9_review.md`
Source TZ: `docs/work/2026-06-09_prod_demo_guard_TZ.md`

## Verdict

Status: **ACCEPTED**

The blocker from the previous review is resolved.

The previous `REWORK` was caused by preview/staging demo-mode being blocked under realistic Next/Vercel env where `NODE_ENV=production` and `VERCEL_ENV=preview`. The rework changes env classification so preview/staging is resolved before treating `NODE_ENV=production` as production.

---

## What was fixed

## F1. Preview/staging override now works under `NODE_ENV=production`

The guard now derives deployment env from:

```text
VERCEL_ENV || APP_ENV || ""
```

It classifies:

```text
isPreview = deploymentEnv === "preview" || deploymentEnv === "staging"
isExplicitProd = deploymentEnv === "production" || (!isPreview && NODE_ENV === "production")
```

This fixes the previous blocker: `NODE_ENV=production` no longer automatically blocks preview/staging when `VERCEL_ENV=preview` or `APP_ENV=staging`.

## F2. Preview/staging still requires explicit override

Preview/staging demo-mode is still blocked unless:

```text
ALLOW_DEMO_MODE_IN_PREVIEW=true
```

This preserves the original safety requirement.

## F3. Real production still blocks demo-mode even if preview override is true

The new tests include:

```text
NODE_ENV=production
VERCEL_ENV=production
NEXT_PUBLIC_DEMO_MODE=true
ALLOW_DEMO_MODE_IN_PREVIEW=true
=> throws Unsafe production config
```

So `ALLOW_DEMO_MODE_IN_PREVIEW` cannot accidentally open real production.

## F4. Tests added for the exact missing cases

The rework adds tests for:

```text
NODE_ENV=production + VERCEL_ENV=preview + demo=true + allowPreview=true => no throw
NODE_ENV=production + APP_ENV=staging + demo=true + allowPreview=true => no throw
NODE_ENV=production + VERCEL_ENV=preview + demo=true + allowPreview=false => preview config error
NODE_ENV=production + VERCEL_ENV=production + demo=true + allowPreview=true => production config error
```

This directly covers the acceptance checklist from the previous review.

---

## Remaining notes

## N1. CI status not available through GitHub status API

GitHub combined status for the reviewed rework commit returned no statuses/checks through the connector.

So this review is based on repository diff inspection, not on independently observed CI output.

Coder/runner evidence should still be kept in the task log if available:

```text
pnpm test / relevant vitest suite
pnpm guardrails:prod
normal production build with demo=false
negative production build/check with demo=true
```

## N2. Guardrail script remains minimal but acceptable for this packet

The guardrail still mainly catches direct unsafe env and direct demo payload usage in `app/`.

This is acceptable for this packet because the main runtime/build-time safety path is now implemented through `production-guard` and `demo-mode`.

A stronger guardrail can be a later hardening task, not a blocker.

## N3. Unrelated horary typing changes are present in the rework commit

The rework commit also touches `components/readings/horary/horary-answer-view.tsx` to fix TypeScript typing.

This is outside the prod-guard scope, but it is small and appears to be a build/typecheck fix. It does not change the review verdict.

---

## Acceptance checklist

```text
[x] NODE_ENV=production + VERCEL_ENV=preview + demo=true + allowPreview=true does not throw.
[x] NODE_ENV=production + APP_ENV=staging + demo=true + allowPreview=true does not throw.
[x] NODE_ENV=production + VERCEL_ENV=preview + demo=true + allowPreview=false throws preview config error.
[x] NODE_ENV=production + VERCEL_ENV=production + demo=true throws production config error.
[x] NODE_ENV=production + demo=false remains allowed from the original implementation.
[x] Build-time guard remains connected via next.config.mjs from the original implementation.
[x] Runtime demo resolver remains connected via lib/demo-mode.ts from the original implementation.
[x] API error does not fall back to demo payload from the original implementation/tests.
[x] guardrails:prod remains registered from the original implementation.
```

## Final conclusion

`W-PROD-DEMO-GUARD` can be accepted.

No further rework is required for the blocker identified in `2026-06-09_prod_demo_guard_a58d6b9_review.md`.
