# Review: Horary detail error-state cleanup

Date: 2026-06-09
Reviewed commit: 17c6c95307fc315685abede46b1cd09873c69208
Previous review: `docs/work/2026-06-09_horary_4ac0281_review.md`
Verdict: ACCEPTED

## Scope reviewed

Commit message: `fix: follow-up — 403 in polling, retry UI, 403 test`.

Changed files:

- `app/(grace)/readings/horary/[id]/page.tsx`
- `__tests__/horary/horary-error-state.test.tsx`

This commit addresses the residual follow-up items from the previous accepted-with-notes review:

1. Handle `403` during polling the same as `401`.
2. Add retry UI for server/network errors.
3. Add frontend tests for error-state mapping.

## Findings

### F1 — 403 during polling handled as auth

Status: ACCEPTED

Polling now handles `401` and `403` in the same branch:

```ts
if (pollStatus === 401 || pollStatus === 403) {
  clearInterval(interval)
  setLoadError("auth")
}
```

This closes the polling-auth consistency note from the previous review.

### F2 — Retry UI for retryable errors

Status: ACCEPTED

The detail page now treats only `server` and `network` load errors as retryable:

```ts
const isRetryable = loadError === "server" || loadError === "network"
```

For retryable states it renders `Попробовать снова` plus the existing `К списку вопросов` link.

This is a good UX split:

- 404/not-found should not offer fake retry as the main path.
- auth should tell the user to re-authenticate.
- server/network should offer retry.

### F3 — Frontend tests added

Status: ACCEPTED

The test file now covers the relevant state mapping:

- `null` response → `Вопрос не найден`;
- `401` → `Нужно авторизоваться`;
- `403` → `Нужно авторизоваться`;
- `500` → `Сервер временно недоступен`;
- network/TypeError → `Нет соединения`;
- server error → retry button;
- network error → retry button;
- failed/expired question states and refund notice remain covered.

This is enough coverage for this follow-up.

## Verification evidence

Coder/local evidence from user message:

- 496 frontend tests pass.
- 277 backend tests pass.
- Total: 773 passed.

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for `17c6c95307fc315685abede46b1cd09873c69208`.
- No combined GitHub status checks were visible for the commit.

## Residual notes

No blockers found.

One minor future cleanup: the page has duplicated fetch/error-mapping logic in initial load and retry. This can later be extracted into a small helper inside the component or hook, but it is not required now.

## Final decision

ACCEPTED.

The previous follow-up items are closed: `403` polling now maps to auth, server/network states have retry UI, and frontend tests cover the important error-state paths. This completes the horary detail error-state cleanup.
