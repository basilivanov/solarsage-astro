# Slice 14 — secure named campaign admin CLI

## Локальная цель

Добавить operator-only create/status/list-redemptions/disable без admin UI и
без передачи raw token в обычные logs/argv.

## Preconditions

Promo models/service/event registry приняты.

## Разрешённые файлы

- новый `apps/api/app/services/promo_admin_service.py`;
- новый `apps/api/app/cli/__init__.py`;
- новый `apps/api/app/cli/promo_campaign.py`;
- новый `apps/api/tests/test_promo_admin_cli.py`.

## Commands

```text
python -m app.cli.promo_campaign create
python -m app.cli.promo_campaign status
python -m app.cli.promo_campaign list-redemptions
python -m app.cli.promo_campaign disable
```

Status/list/disable принимают только `--campaign-id UUID`, никогда raw token.

## Create contract

Required:

```text
--name
--max-redemptions
```

Defaults/options:

```text
--starts-at now UTC
--activation-days 7
--access-days 30
--bonus-credits 50
unlock_natal true / --no-unlock-natal
--token-length 12, allowed 12..16
```

`--starts-at` принимает только timezone-aware RFC3339 `Z`/offset. Naive input,
end/window overflow и invalid benefits -> safe stderr + non-zero exit, без DB
mutation.

Display name: trim, 1..120 Unicode chars, reject C0/C1 control, newline/tab и
bidi override/isolate controls. Name хранится/возвращается, но не логируется.

Token:

- генерируется внутри process через `secrets` из canonical alphabet;
- минимум одна буква;
- custom `--token` отсутствует;
- unique hash conflict -> bounded regenerate, raw candidates не логируются;
- DB получает только SHA-256 hex.

Success stdout — один JSON document, содержащий raw token/deepLink ровно один
раз. Это intentional secure operator output, не structured log. Остальные
commands token/hash не выводят. Lost token не восстанавливается.

Create output дополнительно показывает worst-case totals:

```text
maximumAccessGrants
maximumBonusCredits = maxRedemptions * bonusCredits
maximumNatalUnlocks
```

## Other commands

- `status`: config, UTC window, active, counter, redemption row count и
  `counterConsistent`; no hash/name optional? Display name разрешён operator
  output, но не structured log.
- `list-redemptions --limit`: internal user UUID, redeemedAt и grant IDs;
  никакого Telegram/profile data.
- `disable`: lock/update/commit, idempotent exit 0; existing grants untouched.

Events `promo.campaign_created/disabled` пишутся только после commit и содержат
campaign UUID/config, не name/token/hash.

## Tests

- token format/entropy invariants under deterministic mocked secrets;
- token appears once only in create stdout, never stderr/log mocks/DB;
- canonical `AstroGrace_Bot` URL from settings;
- timezone-aware parsing and naive rejection;
- display-name control/bidi rejection;
- defaults/custom benefits;
- status/counter consistency;
- redemptions privacy/limit;
- disable idempotence and grants survive;
- commit failure writes no success event/token leak.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_promo_admin_cli.py -q
```

## Out of scope

Admin UI, campaign edit/enable/delete, automatic revocation/compensation,
deployment. Не коммитить и не пушить.

