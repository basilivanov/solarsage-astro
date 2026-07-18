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

## Addendum — menu gate experiment: BotFather override CONFIRMED (2026-07-18)

Controlled read/mutation experiment (dev egress, token memory-only, no code
changes):

1. `getMe`: id=8541896258 AstroGrace_Bot, is_bot=true.
2. `getChatMenuButton` (before): `{"type":"web_app","text":"Открыть мой день ✨","web_app":{"url":"https://astro.vasiliy-ivanov.ru/"}}`
   — the owner had already updated the button TEXT via BotFather (was
   «Открыть AstroGrace»); URL stayed the BotFather root value.
3. `setChatMenuButton {type: default}` → ok:true, read-back UNCHANGED.
4. `setChatMenuButton` web_app «Открыть мой день ✨» →
   `https://astro.vasiliy-ivanov.ru/day/today` → ok:true, read-back
   UNCHANGED (root URL persists).

Conclusion: BotFather owns the menu button for this bot — Bot API accepts
all writes (ok:true) and applies none of them, including the default reset.
This is a platform behavior, not a config error.

Current production state (sync --audit rc 0, identity proven):

- menu button: «Открыть мой день ✨» → `https://astro.vasiliy-ivanov.ru/`
  (web_app). The root route client-redirects to `/day/today`
  (`app/(grace)/page.tsx`), so the launch surface is functionally correct —
  one client-side hop. Exact `/day/today` remains the canonical target IF
  the owner sets it in BotFather (Bot Settings → Menu Button).
- Everything else Telegram-side is configured and proven: bio, description,
  /start webhook responder, /start command, webhook, referral URLs.
