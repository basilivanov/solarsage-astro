# Slice 15 — authenticated per-user promo attempt limiter

## Локальная цель

Ограничить brute/noise attempts по internal authenticated user, не блокируя
разных Telegram users за carrier NAT. Только API-process limiter; Nginx —
следующий slice.

## Preconditions

Promo HTTP API принят. Canonical production пока запускает один Uvicorn worker.

## Разрешённые файлы

- новый `apps/api/app/services/promo_rate_limiter.py`;
- `apps/api/app/api/promo.py`;
- новый `apps/api/tests/test_promo_rate_limiter.py`.

## Contract

```text
key: internal user UUID
shared bucket: preview + redeem
limit: 10 attempts
window: rolling 10 minutes
max keys: 10_000
clock: monotonic, injectable in tests
```

Implementation bounded `OrderedDict`/equivalent:

- prune expired timestamps/keys;
- LRU-evict oldest key при capacity;
- check+record не содержит `await`, поэтому mutation atomic внутри одного event
  loop; не добавлять blocking lock/sleep;
- public result сообщает allowed/retry_after_seconds;
- no token/hash/IP/session cookie in key/state/log.

Router вызывает limiter после `require_session`, до campaign hash lookup.
Denied response:

```text
HTTP 429
Retry-After: bounded integer seconds
detail.code = RATE_LIMITED
safe static message
```

Для denied redeem допустим `promo.redemption_rejected` с RATE_LIMITED и bound
user context; preview отдельный ложный redemption event не пишет.

Module предоставляет explicit test reset helper only under ordinary callable
API, без production debug route.

## Scaling invariant

Это MVP contract только для текущего single worker. Документировать рядом с
module: перед `--workers>1`, multiple API replicas или second ingress limiter
должен перейти в shared store/DB bucket. Restart сбрасывает state и не является
security breach из-за token entropy; Nginx volumetric ceiling остаётся.

## Tests

- 10 allowed, 11th 429, Retry-After;
- window expiry restores allowance;
- preview+redeem share bucket;
- two users с одинаковым mocked IP независимы;
- LRU bound/pruning;
- concurrent coroutine calls never allow >10;
- no token in limiter state/log/error;
- unauthenticated request remains 401, not rate-limited.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_promo_rate_limiter.py tests/test_promo_api.py -q
```

## Out of scope

Redis/shared scaling, Nginx config, campaign capacity. Не коммитить и не
пушить.

