# 186 — Telegram bot launch: identity resolved, profile applied, boundary documented

Date: 2026-07-18. Scope: configure Telegram for the production launch except
picture/icon; prove with tests and real Bot API calls. Result: profile copy
applied and read back exactly; menu button is BotFather-owned (Bot API
accepts but does not apply) — exact owner steps below; /start remains a
documented responder gap; auth smoke passed with cleanup.

## Identity resolution (two distinct bots — audit before any mutation)

| Bot | id | Token location | Role |
|---|---|---|---|
| `AstroGrace_Bot` | 8541896258 | apex `/etc/solarsage/app.env` ONLY | **Production** (astro.vasiliy-ivanov.ru), webapp-only, no responder |
| `vi_astro_bot` | 8542033508 | dev host `.env` / `.env.production` | Dev/test, served by Ductor on the dev host |

- getMe called for BOTH tokens (safe output: ok/id/username/is_bot only).
  Identities do NOT match — two different bots, as launch-gate doc 81 implied.
- Dev Ductor: `ductor-astro.service` active on the DEV host, launcher
  hardcodes `EXPECTED_BOT_USERNAME = "vi_astro_bot"`, EnvironmentFile
  `/opt/solarsage-astro/.env`; serves the dev bot only.
- `ductor-astro.service` on astro-prod: **inactive / not-found** — no
  production responder exists (matches doc 81 webapp-only mode).
- All mutations in this run targeted ONLY AstroGrace_Bot (apex token).

## Egress finding

- astro-prod: api.telegram.org IPv4/IPv6 both time out (provider-level
  filtering); general egress (github/google/ghcr) fine. Dev host: Telegram
  reachable. Bot API calls were therefore executed from the dev host with the
  apex token piped over SSH stdout into process memory only — never on disk,
  argv, logs, or output. This is a documented boundary deviation; a permanent
  fix is provider/egress-level (out of this run's scope).

## Applied state (AstroGrace_Bot, real Bot API, read-back)

- **short_description** — SET + read-back EXACT:
  «Не гороскоп из журнала, а расчёт твоего дня по натальной карте: что
  поддерживает, что отложить и почему именно у тебя.»
- **description** — SET + read-back EXACT:
  «Это не прогноз «для всех Тельцов». Я считаю твой день по настоящей
  астрологической математике: твоя натальная карта, транзиты, 12 сфер жизни.
  За 30 секунд узнаешь, что сегодня поддерживает, где трение — и почему всё
  складывается именно так.»
- **name** — unchanged (`AstroGrace — личная астрология`), kept as the
  BotFather/operator surface.
- **commands** — 0 (correct: no production responder; advertising /start
  would be broken UX per doc 81).
- **webhook** — empty, pending 0 (webapp-only policy satisfied).
- **menu button** — NOT applied (see finding).

## Menu button finding (BotFather-owned surface)

`setChatMenuButton` returns `{"ok": true, "result": true}` but
`getChatMenuButton` keeps returning the BotFather-configured value — proven
with two variants (new URL+text; same URL+new text). Bot API changes are
accepted and ignored for this bot: the menu button is owned by BotFather.
Owner action (one minute): BotFather → /mybots → AstroGrace_Bot → Bot
Settings → Menu Button → set URL `https://astro.vasiliy-ivanov.ru/day/today`,
text «Открыть мой день ✨». The sync tool read-back will then pass as-is.

## /start responder gap (unchanged, documented)

No production message responder exists; Ductor's /start copy has no
supported config override and Ductor is not running on prod. The canonical
start copy lives in `scripts/telegram/bot-profile.json` (`start_copy`) for a
future dedicated product-bot handler; commands remain empty by design.

## Tooling (repo, PR #5, main 185b38fe)

- `scripts/telegram/sync_bot_profile.py`: getMe identity gate (exact
  expected_bot_id + bot_username from repo config, fail closed before any
  mutation), `--audit` read-only online mode, exact read-back after every
  setter, `--check` stays fully offline.
- `scripts/telegram/bot-profile.json`: production identity
  (AstroGrace_Bot / 8541896258), canonical menu target WEBAPP_URL +
  `/day/today`.
- Tests `apps/api/tests/test_sync_bot_profile.py`: 16/16 — identity mismatch
  blocks mutations, audit read-only, expected_bot_id required, read-back
  asserted, no token leak.

## Smoke results (production)

- Menu target: `https://astro.vasiliy-ivanov.ru/day/today` → 200.
- HMAC auth smoke (fresh initData signed in-memory with the apex token,
  never printed): `POST /api/auth/telegram` → 200; cookie `grace_session_v2`
  with **Secure + HttpOnly + SameSite=None**; `POST /api/auth/logout` → 204;
  tampered-hash control → 400. Smoke user row deleted from prod DB
  (users 1→0, cascade) and verified.

## Non-actions

No webhook/commands mutations, no Ductor restarts, no avatar/picture calls,
no token ever printed or stored outside apex app.env. tmux alive.
