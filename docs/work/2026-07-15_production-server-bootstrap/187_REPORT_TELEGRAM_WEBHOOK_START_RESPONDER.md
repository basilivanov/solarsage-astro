# 187 — Production /start responder live: webhook, no Ductor (2026-07-18)

Result: **/start works in production on AstroGrace_Bot** via a stateless
FastAPI webhook. No Ductor, no outbound api.telegram.org from apex (Telegram
executes the returned sendMessage itself — Bot API method JSON contract).

## Implementation (PR #7, release 9bd7ff4c1694600190651bac6013cf1ca974d6d9)

- `apps/api/app/api/telegram_webhook.py` — `POST /api/telegram/webhook`:
  - `X-Telegram-Bot-Api-Secret-Token` checked with `hmac.compare_digest`,
    fail-closed (empty configured secret → 403 for everything).
  - Only private `message` updates with text starting `/start` (payload
    included) get a reply; every other valid update → `200 {}`.
  - Reply: Bot API method JSON `sendMessage` with the canonical start copy
    (sync-tested byte-exact vs `scripts/telegram/bot-profile.json`
    `start_copy.text`) and an inline `web_app` button «Открыть мой день ✨»
    → `https://<APP_DOMAIN>/day/today`.
  - Stateless: no DB, no network, **no PII and no raw update bodies in logs**
    (test-proven).
- `config.py`: `TELEGRAM_WEBHOOK_SECRET` setting; compose passes it
  fail-closed (`${TELEGRAM_WEBHOOK_SECRET:?}`). Secret generated with
  `openssl rand -hex 32` on apex into `/etc/solarsage/app.env` (root:astro
  0640, never printed).
- `scripts/telegram/setup_webhook.py` — manual-gated registration:
  identity gate → `setWebhook` (url, `secret_token` redacted,
  `allowed_updates=["message"]`, `drop_pending_updates=true`) →
  `setMyCommands` (`/start` only — a real responder now exists per doc 81)
  → exact read-back. Reuses `sync_bot_profile` shared blocks.
- Tests: `test_telegram_webhook.py` 11/11 (secret gate missing/wrong/
  empty-config, exact copy+button, payload, group/non-start/non-message ack,
  malformed JSON, bot-profile sync, no PII/secret in logs);
  `test_setup_webhook.py` 7/7 (offline check, exact payload, read-back,
  identity block, secret length gate, no leaks). Total telegram suites 34/34.

## Production proofs

- Deploy: workflow run 29663534474 — build+deploy success via forced
  command; active release `9bd7ff4c…`, previous `750d818…` recorded.
- Loopback health ×3 exact `release_sha=9bd7ff4c…`.
- Webhook HTTPS smoke (synthetic update, real secret, memory-only):
  correct secret → `200`, `method=sendMessage`, `chat_id` echoed, exact
  start text, button → `https://astro.vasiliy-ivanov.ru/day/today`;
  wrong secret → `403`.
- Real Bot API registration (dev egress, token/secret memory-only):
  `setWebhook` ok, `setMyCommands` ok; read-back `getWebhookInfo` url +
  allowed_updates EXACT, `getMyCommands` EXACT (one `/start`).

## Remaining manual gate (unchanged)

BotFather menu button (URL `https://astro.vasiliy-ivanov.ru/day/today`,
text «Открыть мой день ✨») — Bot API does not apply it for this bot
(documented in 186). Everything else Telegram-side is configured: bio,
description, /start responder, commands, webhook.

No tokens/secrets printed anywhere. tmux alive.
