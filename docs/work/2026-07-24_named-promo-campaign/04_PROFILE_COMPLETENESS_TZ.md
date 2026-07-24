# Slice 04 — base and natal profile readiness contracts

## Локальная цель

Сделать base onboarding и strict natal completeness публично переиспользуемыми
promo service, не меняя ordinary onboarding product semantics.

## Разрешённые файлы

- `apps/api/app/services/profile_service.py`;
- `apps/api/app/services/natal_context_service.py`;
- новый `apps/api/tests/test_profile_readiness.py`.

## Реализация

Добавить pure public API, например:

```py
def missing_onboarding_fields(profile: UserProfile) -> list[str]

@staticmethod
def missing_profile_fields(profile: UserProfile) -> list[str]

@staticmethod
def is_profile_complete(profile: UserProfile) -> bool
```

Base required set:

```text
birthday
birth_city
gender in {male,female}
```

Strict natal set остаётся:

```text
birthday
birth_time
birth_lat
birth_lon
birth_tz
gender in {male,female}
```

Требования:

- deterministic field order;
- invalid non-null gender возвращается как missing/invalid `gender`;
- `birth_city` не входит в hash-required set; coordinates/timezone являются
  каноническими inputs расчёта;
- existing `_validate_profile_completeness` делегирует новому helper и сохраняет
  прежний HTTP 409 shape для natal consumers;
- `profile_service.update_profile` использует base helper при выставлении
  `is_onboarded`; он не начинает требовать exact time;
- `compute_profile_hash` не меняется;
- existing one-way `is_onboarded` persistence semantics не расширяются вне
  делегирования той же base-проверке;
- Ordinary onboarding contract не ужесточается: его `unknown birth time`
  остаётся допустимым. Promo-specific UI, который обязан запросить exact time
  для `unlock_natal=true`, реализуется отдельным slice; helper только честно
  сообщает natal readiness.

Обновить module contract/map public entrypoints.

## Tests

- каждый required field по одному отсутствует -> exact field;
- base complete + unknown time -> base true, natal false;
- invalid gender -> `gender`;
- complete profile -> empty list/true;
- natal private validation по-прежнему raises 409 с existing message and
  `missingFields`;
- `birth_time=None` при `is_onboarded=true` всё равно возвращает
  `missing_fields=["birth_time"]` и не мутирует profile;
- hash output для существующего complete fixture не изменился.

## Targeted verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_profile_readiness.py -q
```

## Out of scope

Onboarding UI, profile schema, promo redirect, birth data repair, sidecar call.
Не коммитить и не пушить.
