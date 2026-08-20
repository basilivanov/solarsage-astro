# 02 TZ: backend — auto-apply pending промокода при завершении онбординга

- **Packet**: PROMO-PERSIST-02
- **Phase / Wave**: W-NAMED-PROMO-CAMPAIGN (расширение)
- **Modules**: M-PROFILE.api (put_profile), M-PROMO-CAMPAIGN-SERVICE (только вызов)
- **Depends**: PROMO-PERSIST-01 (колонка `users.pending_promo_token` уже есть)

## Goal

Когда пользователь с сохранённым `pending_promo_token` завершает онбординг
(PUT /api/profile → профиль валиден и `is_onboarded = true`), бэкенд сам
применяет промокод через `PromoCampaignService.redeem()` и очищает интент.

## Exact write scope

- `apps/api/app/api/profile.py` — в `put_profile` ПОСЛЕ существующего
  `await db.commit()` добавить блок auto-apply:
  1. Загрузить `User` по user_id; если `user.pending_promo_token` пуст или
     `profile.is_onboarded` false → выйти.
  2. `try: await PromoCampaignService(db).redeem(user_id, user.pending_promo_token)`
     → успех: `user.pending_promo_token = None`, `await db.commit()`.
  3. `except PromoDomainError as err`: очистить токен и commit для терминальных
     кодов (`INVALID_CODE`, `CAMPAIGN_EXPIRED`, `CAMPAIGN_FULL`,
     `ALREADY_REDEEMED`); для `PROFILE_INCOMPLETE` токен СОХРАНИТЬ
     (пользователь дозаполнит профиль позже). В обоих случаях лог
     `promo.pending_auto_apply_failed` с payload `{"error_code": err.code}`
     (БЕЗ токена). Внимание: redeem в своей error-ветке делает rollback —
     профиль уже закоммичен выше, так что это безопасно.
  4. `except Exception`: `await db.rollback()`, лог
     `promo.pending_auto_apply_failed` с `{"error_code": "UNEXPECTED"}`,
     НЕ поднимать исключение — ответ PUT /api/profile остаётся 200.
- `apps/api/app/core/logging_events.py` — добавить
  `"promo.pending_auto_apply_failed"` в секцию promo campaigns.
- `apps/api/tests/test_promo_pending_auto_apply.py` — новый тест-файл
  (паттерны моков/fixtures брать из `tests/test_promo_campaign_service.py` и
  `tests/test_profile_endpoints.py`; для создания кампании смотри, как это
  делают существующие promo-тесты).

## Frozen / out-of-scope

- НЕ менять `promo_campaign_service.py` (redeem используется как есть).
- НЕ менять auth.py, models.py, миграции (это срез 01, уже принят).
- НЕ трогать фронтенд.

## Must-preserve invariants

- PUT /api/profile всегда отвечает как раньше (200 + ProfileRead), даже если
  redeem падает любой ошибкой.
- Профиль коммитится ДО попытки redeem; ошибка redeem не откатывает профиль.
- redeem сам делает единственный свой commit/rollback — не нарушать его
  контракт, не вызывать его внутри незакоммиченной транзакции профиля.
- raw token не попадает в логи.
- Пользователь без pending token: поведение PUT байт-в-байт как раньше
  (никаких лишних запросов/локов).

## Критерии (тесты)

1. Пользователь с pending token + активная кампания завершает онбординг
   (PUT profile с полными данными) → 200, в БД есть `PromoRedemption`,
   выдан доступ (AccessLedger) согласно кампании, `pending_promo_token`
   очищен.
2. Просроченная кампания → 200, профиль сохранён, redemption нет,
   pending token очищен.
3. Пользователь без pending token → обычный 200, ничего не меняется.

## Verification

```bash
cd apps/api && source .venv/bin/activate && \
python -m pytest tests/test_promo_pending_auto_apply.py tests/test_profile_endpoints.py tests/test_promo_campaign_service.py -q
```

## Expected evidence

- Список изменённых файлов, вывод pytest, `git diff --stat`.

## Escalation

Понадобилось менять promo service / auth / фронт → стоп, доложить, ждать
новый packet.

## No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
