# Slice 16 — Nginx start-param privacy and loose volumetric ceiling

## Локальная цель

Не допустить raw `tgWebAppStartParam` в transport logs и добавить loose
ingress-level abuse ceiling без product-level NAT false positives.

## Разрешённые файлы

- `infra/nginx/astro.vasiliy-ivanov.ru.conf`;
- новый `apps/api/tests/test_nginx_promo_privacy.py` либо другой узкий static
  infra test file.

Не редактировать live `/etc/nginx` в coder iteration.

## Privacy log contract

Site config, включаемый в Nginx `http` context, объявляет named log format и
переопределяет access log для обоих server blocks:

- request component: `$request_method $uri $server_protocol`;
- запрещены `$request`, `$request_uri`, `$args`, `$query_string`;
- raw `$http_referer` не логируется;
- status/bytes/timing/correlation-safe operational fields сохраняются;
- error log не повышать до debug.

Response `Referrer-Policy` меняется с `strict-origin-when-cross-origin` на
`strict-origin`, чтобы same-origin static/API requests не переносили полный
query URL. Это согласовано с browser `history.replaceState` из Slice 01.

## Volumetric limiter

```text
key: $binary_remote_addr
rate: 120r/m
burst: 60 nodelay
scope: exact anchored /api/promo/(preview|redeem)
status: 429 JSON RATE_LIMITED
```

Это не product per-user limit. Location обязан полностью повторить canonical
API proxy contract: upstream 8000, HTTP version, timeouts, Host/real/forwarded
headers и Set-Cookie pass. Не допустить, чтобы regex/exact location случайно
обошёл generic proxy settings.

Для promo location установить `client_max_body_size 1k`; body должен содержать
только короткий JSON token. Generic API limit 5m не менять.

## Tests

Static assertions:

- privacy format не содержит запрещённых variables/Referer;
- оба server block используют named format;
- strict-origin exact;
- promo location anchored, rate/burst/status exact;
- promo body cap 1k;
- canonical proxy headers/timeouts/cookies присутствуют;
- generic `/api/` и frontend proxy остаются.

Operator acceptance после review, не coder action:

```text
install repo config canonical host path
remote repo/installed sha256 equal
nginx -t
systemctl reload nginx
nginx -T proof
synthetic tgWebAppStartParam canary absent from access/error logs
```

Privacy config является rollback floor и не удаляется при rollback promo UI.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_nginx_promo_privacy.py -q
```

## Out of scope

Live host mutation/reload, application limiter, frontend gate. Не коммитить и
не пушить.
