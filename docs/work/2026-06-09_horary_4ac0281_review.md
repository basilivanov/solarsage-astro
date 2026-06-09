# Review: Horary detail error handling follow-up

Date: 2026-06-09
Reviewed commit: 4ac028114288ca45272a28f94a5f010b66f01a33
Previous review: `docs/work/2026-06-09_horary_433db53_review.md`
Verdict: ACCEPTED WITH NOTES

## Scope reviewed

Commit message: `fix: horary detail page distinguishes error types`.

Changed file:

- `app/(grace)/readings/horary/[id]/page.tsx`

This follow-up targets the remaining B1 blocker from the previous review: the horary detail page incorrectly rendered thrown load/server/API errors as `Вопрос не найден`.

## Findings

### B1 — thrown load errors no longer render as not-found

Status: ACCEPTED

The detail page now separates states:

- `getHoraryQuestion(id) === null` → `loadError = "not_found"`;
- `HoraryApiError` with `401/403` → `loadError = "auth"`;
- `HoraryApiError` with `>=500` → `loadError = "server"`;
- non-`HoraryApiError` exception → `loadError = "network"`.

The rendered copy now distinguishes:

- `Нужно авторизоваться`;
- `Сервер временно недоступен`;
- `Нет соединения`;
- `Вопрос не найден` only for the fallback/not-found branch.

This fixes the failure-handling issue: server/load failures are no longer presented as an expired link or deleted question.

### Polling behavior

Status: ACCEPTED WITH NOTE

Polling now aborts and renders auth state on `HoraryApiError` with status `401`.

Small follow-up note: initial load handles both `401` and `403` as auth, but polling only checks `401`. If the backend can return `403` during polling, it should also abort and show auth. This is not a blocker for the original B1 because initial load is now correct and server errors are no longer masked as not-found.

### Tests / CI

Status: NOTE

This commit is a surgical frontend fix and does not add tests. The previous review asked for frontend tests for this exact behavior; this remains recommended.

Suggested future tests:

- detail page 404 renders `Вопрос не найден`;
- detail page 401/403 renders `Нужно авторизоваться`;
- detail page 500 renders `Сервер временно недоступен`;
- thrown network error renders `Нет соединения`.

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for `4ac028114288ca45272a28f94a5f010b66f01a33`.
- No combined status checks were visible for the commit.

## Final decision

ACCEPTED WITH NOTES.

The remaining B1 blocker from the previous review is fixed. Server/auth/network failures are no longer masked as `Вопрос не найден`. The only residual notes are frontend test coverage and optionally handling `403` during polling the same way as `401`.
