# Slice 08 — authenticated promo preview/redeem HTTP surface

## Локальная цель

Экспонировать готовый domain service через два session-authenticated POST
endpoint с safe/no-store contract. Nginx rate limit приходит отдельным slice.

## Preconditions

Slices 06–07 приняты.

## Разрешённые файлы

- новый `apps/api/app/api/promo.py`;
- `apps/api/app/main.py`;
- новый `apps/api/tests/test_promo_api.py`;
- при необходимости import-only `apps/api/app/api/__init__.py`.

## Endpoints

```text
POST /api/promo/preview
POST /api/promo/redeem
```

Оба:

- use `PromoCodeRequest`;
- use authenticated internal `User` from `require_session`;
- body token извлекается через `SecretStr.get_secret_value()` только в local
  call expression/service boundary;
- response model exact generated Pydantic contract;
- `Cache-Control: no-store`;
- no request/body/token logging;
- no GET/query/cookie token variant;
- unauthenticated -> existing canonical 401 session error.

Default FastAPI/Pydantic 422 для promo body запрещён: он включает raw invalid
`input`. Использовать route-scoped safe parsing/exception boundary, который:

- принимает только JSON object с string `token`;
- имеет малый body/content-length cap;
- на malformed JSON/type/missing/extra fields возвращает
  `400 {detail:{code:INVALID_CODE,...}}`;
- никогда не echo input/body;
- не меняет validation behavior других API routes.

Предпочтительный bounded implementation — локальный
`APIRoute`/`get_route_handler` wrapper в `api/promo.py`, который ловит
`RequestValidationError` только для promo router и возвращает safe 400. Это
сохраняет `PromoCodeRequest` в OpenAPI и не требует global exception handler.

Route конвертирует internal dataclasses в Pydantic, но не реализует business
checks и grants повторно.

## Error mapping

Domain error -> `HTTPException(detail={code,message})`:

```text
INVALID_CODE       400
CAMPAIGN_EXPIRED   410
CAMPAIGN_FULL      409
ALREADY_REDEEMED   409
PROFILE_INCOMPLETE 409
```

Unexpected exception не отправляет raw detail клиенту и не превращается в
`INVALID_CODE`; canonical 500 boundary/logging handles it. Domain service уже
rollback-нул transaction.

Length/alphabet invalid string должен reach service и вернуть `INVALID_CODE`.
Не ставить Pydantic min/max/pattern, не регистрировать global validation handler
с побочным изменением всего API.

## Preview specifics

- valid/incomplete -> 200 with `profileComplete=false`;
- no mutation/counter;
- full/expired/already use same safe codes;
- offer never includes campaign ID/hash/token.

## Redeem specifics

- one call to service; route itself не commit;
- success exact offer/grants mapping;
- duplicate is 409 state-idempotent, not a second 200 grant.

## Tests

- router mounted in production `create_app`;
- unauthenticated both endpoints 401;
- valid session preview/redeem success shapes and no-store;
- incomplete preview 200, incomplete redeem 409/no mutation;
- exact status/code matrix;
- response/error never contains token, hash, display name in error, internal
  campaign/grant IDs;
- short/long/numeric/null/object/malformed JSON sentinel отсутствует во всём
  response body и captured logs;
- request repr/log capture does not contain token;
- main public-surface/security tests remain green.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_promo_api.py tests/test_public_surface_security.py -q
```

## Out of scope

Per-user/Nginx rate limiter, frontend, CLI, full suite. Не коммитить и не
пушить.
