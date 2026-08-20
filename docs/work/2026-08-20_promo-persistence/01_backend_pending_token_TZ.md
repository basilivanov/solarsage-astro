# 01 TZ: backend — сохранение pending_promo_token при /api/auth/telegram

- **Packet**: PROMO-PERSIST-01
- **Phase / Wave**: W-NAMED-PROMO-CAMPAIGN (расширение)
- **Modules**: M-AUTH-TG.api, M-AUTH-TG.service, M-AUTH-TG.models, новый M-MIGRATION-0032

## Goal

При логине с promo `start_param` бэкенд сохраняет токен в
`users.pending_promo_token`, чтобы интент переживал перезапуск webview.

Контекст: Telegram включает `start_param` в ПОДПИСАННЫЙ initData (проверено:
`auth.py` уже считает `"start_param=" in body.init_data`). HMAC-проверка
покрывает start_param, значит ему можно доверять после `verify_init_data`.

## Exact write scope

- `apps/api/app/db/models.py` — добавить в `User`:
  `pending_promo_token: Mapped[str | None] = mapped_column(String(16), nullable=True)`
  (рядом с tg_username; обновить MODULE_MAP/комментарии модели).
- `apps/api/alembic/versions/0032_pending_promo_token.py` — новая миграция
  (стиль как `0031_checkin_observed_spheres.py`, включая GRACE-шапку):
  `revision = "0032_pending_promo_token"`,
  `down_revision = "0031_checkin_observed_spheres"`,
  upgrade: `op.add_column("users", sa.Column("pending_promo_token", sa.String(16), nullable=True))`,
  downgrade: `op.drop_column("users", "pending_promo_token")`.
- `apps/api/app/services/telegram_auth.py` — новая публичная функция
  `parse_start_param(raw: str) -> str | None`: чистый парс через существующий
  `_parse_init_data`, возвращает `parsed.get("start_param")` или None.
  В FUNCTION_CONTRACT явно: вызывать ТОЛЬКО после успешного
  `verify_init_data` (HMAC уже проверен); сама функция HMAC не проверяет.
- `apps/api/app/api/auth.py` — в `auth_telegram` после `verify_init_data`:
  `start_param = parse_start_param(body.init_data)`; если start_param
  fullmatch `PROMO_TOKEN_REGEX` (импорт из
  `app.services.promo_campaign_service`) → `user.pending_promo_token = start_param`
  до существующего `await db.commit()`.
- `apps/api/app/core/logging_events.py` — добавить событие
  `"promo.pending_token_saved"` в секцию promo campaigns; эмитить его в
  auth.py при сохранении (payload БЕЗ токена: например `{"source": "start_param"}`).
- `apps/api/tests/test_auth_endpoints.py` — новые тесты (см. критерии).
  Если фикстура `make_initdata` не умеет start_param — расширить её
  опциональным параметром (совместимо с существующими вызовами).

## Frozen / out-of-scope

- НЕ трогать `promo_campaign_service.py`, `profile.py`, фронтенд.
- НЕ менять поведение `/api/auth/dev`.
- НЕ менять `verify_init_data` и его возвращаемый тип.

## Must-preserve invariants

- Логин БЕЗ start_param НЕ затирает существующий `pending_promo_token`.
- Реферальный (числовой) или невалидный start_param НЕ сохраняется.
- raw token не попадает ни в один лог/ответ (ни payload, ни message).
- Существующие тесты auth не ломаются; HMAC-инварианты auth.py сохранены.
- GRACE-разметка (AI_HEADER/MODULE_CONTRACT/FUNCTION_CONTRACT) по AGENTS.md.

## Verification

```bash
cd apps/api && source .venv/bin/activate && \
python -m pytest tests/test_auth_endpoints.py tests/test_alembic_roundtrip.py -q
```

## Expected evidence

- Список изменённых файлов, вывод pytest (все зелёные),
  `git diff --stat`.

## Escalation

Нужен соседний scope (promo service, profile API, frontend) → стоп,
доложить в отчёте, ждать новый packet.

## No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
