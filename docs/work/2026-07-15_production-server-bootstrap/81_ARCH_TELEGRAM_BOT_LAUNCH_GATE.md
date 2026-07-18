# Architecture — Telegram/BotFather production launch gate

## Current gap

Current loader/deploy checks only non-empty `TELEGRAM_BOT_TOKEN` and configured string `BOT_USERNAME`. A valid token belonging to another bot can pass. Production identity must be proven through Bot API `getMe` with exact non-secret bot ID and username.

No network/apply is performed while implementing this architecture. Real token never appears in argv, process list, logs, evidence or docs.

## Repo-owned desired-state profile

Add non-secret `infra/production/telegram-bot-profile.json`:

```text
schema_version
expected_bot_id
expected_username = AstroGrace_Bot
mode = webapp_only
webapp_url = https://astro.vasiliy-ivanov.ru/
name
short_description
description
menu_button_text
commands/scopes/languages
webhook_policy
avatar asset path + SHA256/evidence policy
```

Suggested copy:

- name: `AstroGrace`;
- menu: `Открыть AstroGrace`;
- short: `Личный астрологический навигатор: главные темы дня, сроки и понятные действия по вашей карте.`;
- description: понятное объяснение личного периода в трёх горизонтах без фатальных обещаний и астрологического жаргона.

Validate all Bot API length/character limits before any call.

## Safe server-side gate

Use Python/httpx or equivalent library, not shell `curl https://api.telegram.org/bot<TOKEN>/...` where token appears in argv/process lists.

Runner:

- reads token only from server profile/credential;
- debug/xtrace disabled;
- never prints raw Bot API URL/body/initData/token prefix/suffix;
- diagnostics expose only check name, safe bot ID/username, contract hash, release/correlation ID;
- evidence JSON root-owned and non-secret;
- read-only `--check` and explicit idempotent `--apply` are separate.

## Gate stages

### 1. Static secret/security

- secret regular non-symlink correct owner/mode;
- token absent from GitHub deploy secrets, frontend/sidecar/build env, unit command line and release manifest;
- exact HTTPS production host.

### 2. Identity — always before mutation

`getMe` must prove:

```text
ok = true
result.is_bot = true
result.id = expected_bot_id
result.username = AstroGrace_Bot
```

Expected ID is a separate non-secret integer, not parsed from token. Any mismatch/401/429/timeout/malformed response blocks profile mutation and restart.

### 3. Profile reconciliation (`--apply` only)

Idempotent set + exact read-back:

- name;
- description;
- short description;
- default chat menu button exact WebApp URL/text;
- commands only when an actual production message responder exists.

Current repo has no production Telegram message/webhook responder. Therefore commands should remain empty; advertising `/start`, `/today` etc. would create broken UX. WebApp menu is the launch surface.

### 4. Webhook policy

For current webapp-only mode, `getWebhookInfo.url` must be empty. Stale webhook deletion/drop pending updates is a separate explicit `--apply` + operator confirmation, never read-only behavior.

### 5. URL/release readiness

- DNS/TLS exact host;
- no foreign/cross-host redirect;
- frontend 200 and exact release identity;
- menu button URL exact;
- manual Telegram iOS/Android/Desktop WebView proof remains mandatory.

### 6. Application dependency readiness

Public `/api/health` is liveness only. Private/local launch gate verifies:

- API exact release SHA;
- authenticated DB `SELECT 1`;
- Alembic current=head;
- sidecar exact release/calculation/ephemeris identity;
- frontend release identity;
- secure session cookie/CORS policy;
- Telegram HMAC/auth smoke;
- LLM/GeoNames status according to explicit feature-criticality policy.

Do not expose dependency details publicly.

## HMAC/auth smoke

### Mandatory local cryptographic test

In memory only:

- fresh synthetic initData signed with current token → success;
- one-byte tamper → invalid HMAC;
- expired/future auth_date → rejected;
- no initData/token output.

### Public API integration

`POST /api/auth/telegram` mutates User/Profile/Session. Use either:

- reserved launch-smoke Telegram user plus exact session/row cleanup; or
- operator account with explicit evidence and logout/session revoke.

Assert `Secure`, `HttpOnly`, `SameSite=None`, authenticated safe read and cleanup. Existing `generate-telegram-test-initdata.py` prints full initData/URL and falls back to checkout `.env.production`; it is not suitable for production gate.

## Avatar/operator boundary

Repo asset requirements:

- 512×512 PNG;
- safe circular crop margins;
- readable light/dark appearance;
- no small text;
- SHA256 recorded.

Avatar upload remains BotFather/operator-owned. Bot API may only prove a profile photo exists, not pixel identity. Operator records screenshot/evidence from real clients.

## Secret placement

- production token stays server-side only in API profile/credential;
- never GitHub Actions deploy secret;
- `E2E_TELEGRAM_BOT_TOKEN` is a separate test-bot secret, never production token;
- token absent from frontend, sidecar, build and release status;
- future `systemd LoadCredential` is stronger, but profile env is acceptable minimal migration if exact consumer boundary from `70_TZ...` is enforced.

## Rotation runbook

1. Operator generates/revokes via BotFather without chat/docs/history copy.
2. Atomically stage new server secret.
3. Before restart, `getMe` new token must prove same exact ID/username.
4. Restart only API/actual bot consumers.
5. HMAC smoke, profile/menu/webhook read-back and real Telegram launch.
6. Existing app sessions should remain valid; new login uses new token-signed initData.
7. Revoked old token is not rollbackable; rollback means issue another new token.

Evidence/journal never contains token. Verify webhook/profile after rotation.

## Automation vs operator

Automatable through Bot API:

- getMe;
- set/get name, description, short description;
- set/get default chat menu button;
- set/get commands/scopes;
- getWebhookInfo and explicitly confirmed webhook mutation;
- exact read-back/idempotence.

Operator/BotFather:

- create bot, choose username, ownership/security;
- issue/revoke token;
- upload avatar and visually verify;
- any legacy domain binding if actually required;
- final real-client WebView/auth proof.

## Acceptance matrix

- getMe correct/wrong ID/wrong username/is_bot false/401/429/timeout/malformed;
- token never in argv/log/evidence/error;
- profile schema/length/URL validation;
- apply/read-back/idempotence;
- HTTP/foreign URL/redirect rejected;
- stale webhook policy;
- HMAC valid/wrong token/tamper/expired/future/missing/duplicate fields;
- negative auth creates no DB rows;
- auth cookie/read/logout cleanup;
- DB/sidecar/Alembic/release/CORS/cookie failures block;
- rotation same bot passes, different bot blocks before restart, revoked old fails;
- manual iOS/Android/Desktop menu/auth/reload and avatar evidence.

Launch is blocked by identity/HMAC/menu/TLS/release/DB/Alembic/sidecar/secret-boundary failures. External provider failures are WARN or BLOCK only according to explicit enabled-feature policy.
