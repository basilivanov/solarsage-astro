# Review: W-PROD-DEMO-GUARD after commit a58d6b9

Date: 2026-06-09
Reviewed commit: `a58d6b93c09cd65280125a9bad559be1dff9294c`
Source TZ: `docs/work/2026-06-09_prod_demo_guard_TZ.md`

## Verdict

Status: **REWORK**

The implementation is mostly in the right direction, but one acceptance-critical case is wrong:

```text
Preview/staging demo-mode with explicit ALLOW_DEMO_MODE_IN_PREVIEW=true must be allowed.
In the current implementation, realistic preview builds can still fail because NODE_ENV=production is treated as production before preview override is considered.
```

This is a blocker because the TZ explicitly requires preview/staging demo-mode to be allowed only with an override.

---

## What is good

## G1. Build-time guard is connected

`next.config.mjs` imports `assertProductionSafety()` and runs it before exporting Next config.

This means unsafe config can fail before the app is built.

## G2. Runtime demo-mode resolver is connected

`lib/demo-mode.ts` now resolves demo mode through `assertProductionSafety()` instead of directly reading `NEXT_PUBLIC_DEMO_MODE`.

This gives a runtime backstop for code paths that import demo-mode.

## G3. Production demo-mode is blocked

`assertProductionSafety()` throws when demo-mode is enabled in production.

This satisfies the main production-safety goal.

## G4. API error fallback test was added

A test checks that `fetchDay()` rejects on API 500 and does not return demo data when demo-mode is false.

## G5. Guardrail script exists

`package.json` now has:

```text
guardrails:prod
```

and `scripts/check_prod_guard.sh` checks `.env.production`, `.env.example`, and raw demo payload references in `app/`.

## G6. Env docs were updated

`.env.example` now documents:

```text
NEXT_PUBLIC_DEMO_MODE=false
ALLOW_DEMO_MODE_IN_PREVIEW=false
```

---

# Blockers

## B1. Preview/staging override is broken in realistic Next/Vercel env

### Problem

Current guard logic:

```ts
const isProd = nodeEnv === "production" || appEnv === "production" || vercelEnv === "production"
const isPreview = appEnv === "preview" || appEnv === "staging" || vercelEnv === "preview"

if (isProd && demoMode) {
  throw new Error("Unsafe production config...")
}

if (isPreview && demoMode && !allowPreview) {
  throw new Error("Unsafe preview config...")
}
```

In real Next/Vercel preview builds, `NODE_ENV` is normally `production`, while `VERCEL_ENV=preview`.

So this env:

```text
NODE_ENV=production
VERCEL_ENV=preview
NEXT_PUBLIC_DEMO_MODE=true
ALLOW_DEMO_MODE_IN_PREVIEW=true
```

will still fail the first `isProd && demoMode` branch before preview override is considered.

### Why this violates TZ

The TZ required:

```text
Preview/staging demo-mode is allowed only when ALLOW_DEMO_MODE_IN_PREVIEW=true.
```

Current tests do not cover the realistic case because the positive preview test sets `APP_ENV=preview` but does not also set `NODE_ENV=production`.

### Required fix

Classify deployment env before generic production check.

Recommended logic:

```ts
const deploymentEnv = process.env.VERCEL_ENV || process.env.APP_ENV || ""
const isPreview = deploymentEnv === "preview" || deploymentEnv === "staging"
const isExplicitProd = deploymentEnv === "production" || (!isPreview && process.env.NODE_ENV === "production")

if (isPreview && demoMode && !allowPreview) {
  throw new Error("Unsafe preview config: NEXT_PUBLIC_DEMO_MODE=true requires ALLOW_DEMO_MODE_IN_PREVIEW=true")
}

if (isExplicitProd && demoMode) {
  throw new Error("Unsafe production config: NEXT_PUBLIC_DEMO_MODE=true is forbidden in production")
}
```

Or equivalent.

### Required tests

Add these cases:

```text
NODE_ENV=production
VERCEL_ENV=preview
NEXT_PUBLIC_DEMO_MODE=true
ALLOW_DEMO_MODE_IN_PREVIEW=true
=> no throw
```

```text
NODE_ENV=production
APP_ENV=staging
NEXT_PUBLIC_DEMO_MODE=true
ALLOW_DEMO_MODE_IN_PREVIEW=true
=> no throw
```

```text
NODE_ENV=production
VERCEL_ENV=preview
NEXT_PUBLIC_DEMO_MODE=true
ALLOW_DEMO_MODE_IN_PREVIEW=false
=> throws preview config error
```

---

# Major issues / follow-up

## M1. Guardrail script is very minimal

Current `scripts/check_prod_guard.sh` checks direct demo payload usage only under `app/`.

The TZ also asked to consider:

```text
lib/api/*
components/today/*
app/(app)/day/*
app/(app)/readings/*
```

This is not a blocker because the current implementation has runtime guard in `lib/demo-mode.ts`, but the guardrail could be strengthened later.

Recommended follow-up:

- allow direct demo imports in `lib/demo-mode.ts`, `lib/demo-data.ts`, and explicitly demo-controlled API clients;
- fail direct demo imports in route/page/components outside controlled paths.

## M2. `@ts-expect-error` in production-guard.ts should be watched

`lib/env/production-guard.ts` imports `./production-guard.mjs` with `@ts-expect-error`.

If TypeScript configuration changes and this import stops producing an error, `@ts-expect-error` itself may become a typecheck failure.

Not a current blocker if the reported tests/build are green, but cleaner options are:

- keep the guard in TypeScript only and import compiled JS from `next.config` differently;
- or add a small declaration file for the `.mjs` module.

---

# Required rework packet

Packet title:

```text
W-PROD-DEMO-GUARD-FIX-1: preview/staging override under NODE_ENV=production
```

Allowed files:

```text
lib/env/production-guard.mjs
lib/env/production-guard.ts
__tests__/lib/production-guard.test.ts
```

Optional:

```text
scripts/check_prod_guard.sh
```

Required changes:

1. Fix env classification so preview/staging can allow demo-mode when override is explicitly true, even if `NODE_ENV=production`.
2. Add tests for realistic Vercel/Next preview env with `NODE_ENV=production` and `VERCEL_ENV=preview`.
3. Keep production env blocked when `VERCEL_ENV=production` or `APP_ENV=production`.
4. Re-run frontend tests/build/guardrails.

---

# Acceptance checklist for rework

```text
[ ] NODE_ENV=production + VERCEL_ENV=preview + demo=true + allowPreview=true does not throw.
[ ] NODE_ENV=production + APP_ENV=staging + demo=true + allowPreview=true does not throw.
[ ] NODE_ENV=production + VERCEL_ENV=preview + demo=true + allowPreview=false throws preview config error.
[ ] NODE_ENV=production + VERCEL_ENV=production + demo=true throws production config error.
[ ] NODE_ENV=production + demo=false does not throw.
[ ] pnpm test / relevant vitest suite passes.
[ ] pnpm guardrails:prod passes.
[ ] Normal production build with demo=false passes.
[ ] Negative production build/check with demo=true fails.
```

## Final note

Do not expand this rework into natal frontend, payment, paywall, or API architecture. The implementation is close; only the preview/staging classification logic needs correction before acceptance.
