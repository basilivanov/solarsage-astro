# ТЗ: Профиль — три локации

## 1. Суть проблемы

Онбординг спрашивает **три локации**: место рождения, текущий город, город на день рождения. Но на бэкенд (`PUT /api/profile`) отправляется **только место рождения**. Города «где живу сейчас» и «где проведу ДР» хранятся исключительно в `localStorage` и теряются при очистке или смене устройства.

**Последствия:**

- `today_service.py` использует `birth_tz` как `current_tz` (комментарий: _«W-3.4: use birth_tz as current_tz (proper current_tz tracking deferred)»_) — транзиты строятся по часовому поясу рождения, а не текущему.
- Хорар не может использовать `current_lat`/`current_lon` — их нет в БД.
- Соляр не может использовать `birthday_lat`/`birthday_lon` — их нет в БД.
- Профильный экран показывает `currentCity`/`birthdayCity` из `localStorage` — после очистки кеша данные пропадут.

## 2. Текущее состояние

### 2.1. Что спрашивает фронт (онбординг)

| Шаг | Поле (state)         | Тип                                   | Куда сохраняется сейчас      |
|-----|----------------------|---------------------------------------|------------------------------|
| 2   | `birthPlace`         | `City` (name, country, lat, lon, tz) | `birth_city`, `birth_lat`, `birth_lon`, `birth_tz` |
| 2   | `sameAsBirth`        | `boolean`                            | **теряется**                 |
| 2   | `currentCity`        | `City`                               | **теряется**                 |
| 3   | `birthdaySameAsCurrent` | `boolean`                         | **теряется**                 |
| 3   | `birthdayCity`       | `City`                               | **теряется**                 |

### 2.2. Что хранит бэкенд (`user_profiles`)

| Колонка      | Тип             | Что              |
|-------------|-----------------|------------------|
| `birth_city` | `String(200)`  | Город рождения (строка) |
| `birth_lat`  | `Numeric(8,5)` | Широта рождения  |
| `birth_lon`  | `Numeric(9,5)` | Долгота рождения |
| `birth_tz`   | `String(64)`   | IANA timezone рождения |

**Нет колонок для:** `current_city`, `current_lat`, `current_lon`, `current_tz`, `birthday_city`, `birthday_lat`, `birthday_lon`, `birthday_tz`.

### 2.3. Кто потребляет локации

| Потребитель          | Что нужно                     | Сейчас берёт                  |
|----------------------|-------------------------------|-------------------------------|
| `today_service.py`   | `current_tz` (для транзитов)  | `birth_tz` (fallback, W-3.4)  |
| `today_service.py`   | `birth_lat`, `birth_lon` (натал) | `birth_lat`, `birth_lon`   |
| Хорар (будущее)     | `current_lat`, `current_lon` (ASC) | — нет в БД               |
| Соляр (будущее)     | `birthday_lat`, `birthday_lon` (соляр-карта) | — нет в БД       |
| Профильный экран    | `currentCity`, `birthdayCity` (для показа) | `localStorage` |

## 3. Изменения

### 3.1. Миграция `0010_add_profile_locations.py`

```python
"""add profile locations (current + birthday)

Revision ID: 0010_add_profile_locations
Revises: dab464195b91
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0010_add_profile_locations'
down_revision = 'dab464195b91'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('current_city', sa.String(200), nullable=True))
    op.add_column('user_profiles', sa.Column('current_lat', sa.Numeric(8, 5), nullable=True))
    op.add_column('user_profiles', sa.Column('current_lon', sa.Numeric(9, 5), nullable=True))
    op.add_column('user_profiles', sa.Column('current_tz', sa.String(64), nullable=True))
    op.add_column('user_profiles', sa.Column('birthday_city', sa.String(200), nullable=True))
    op.add_column('user_profiles', sa.Column('birthday_lat', sa.Numeric(8, 5), nullable=True))
    op.add_column('user_profiles', sa.Column('birthday_lon', sa.Numeric(9, 5), nullable=True))
    op.add_column('user_profiles', sa.Column('birthday_tz', sa.String(64), nullable=True))

    # Data migration: для существующих пользователей копируем birth_* в current_*
    # и birthday_* (предполагаем «живу там же» и «ДР там же» по умолчанию)
    op.execute("""
        UPDATE user_profiles
        SET current_city = birth_city,
            current_lat = birth_lat,
            current_lon = birth_lon,
            current_tz  = birth_tz,
            birthday_city = birth_city,
            birthday_lat = birth_lat,
            birthday_lon = birth_lon,
            birthday_tz  = birth_tz
    """)

    op.create_check_constraint(
        "ck_user_profiles_current_lat_range",
        "user_profiles",
        "current_lat IS NULL OR (current_lat >= -90 AND current_lat <= 90)"
    )
    op.create_check_constraint(
        "ck_user_profiles_current_lon_range",
        "user_profiles",
        "current_lon IS NULL OR (current_lon >= -180 AND current_lon <= 180)"
    )
    op.create_check_constraint(
        "ck_user_profiles_birthday_lat_range",
        "user_profiles",
        "birthday_lat IS NULL OR (birthday_lat >= -90 AND birthday_lat <= 90)"
    )
    op.create_check_constraint(
        "ck_user_profiles_birthday_lon_range",
        "user_profiles",
        "birthday_lon IS NULL OR (birthday_lon >= -180 AND birthday_lon <= 180)"
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_profiles_current_lat_range", "user_profiles")
    op.drop_constraint("ck_user_profiles_current_lon_range", "user_profiles")
    op.drop_constraint("ck_user_profiles_birthday_lat_range", "user_profiles")
    op.drop_constraint("ck_user_profiles_birthday_lon_range", "user_profiles")
    op.drop_column('user_profiles', 'birthday_tz')
    op.drop_column('user_profiles', 'birthday_lon')
    op.drop_column('user_profiles', 'birthday_lat')
    op.drop_column('user_profiles', 'birthday_city')
    op.drop_column('user_profiles', 'current_tz')
    op.drop_column('user_profiles', 'current_lon')
    op.drop_column('user_profiles', 'current_lat')
    op.drop_column('user_profiles', 'current_city')
```

### 3.2. ORM-модель (`apps/api/app/db/models.py`)

Добавить в `UserProfile` после `birth_tz`:

```python
    # Где живу сейчас
    current_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    current_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
    current_tz: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Где отмечаю день рождения (соляр)
    birthday_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    birthday_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    birthday_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
    birthday_tz: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

Добавить в `__table_args__`:

```python
    CheckConstraint(
        "current_lat IS NULL OR (current_lat >= -90 AND current_lat <= 90)",
        name="ck_user_profiles_current_lat_range",
    ),
    CheckConstraint(
        "current_lon IS NULL OR (current_lon >= -180 AND current_lon <= 180)",
        name="ck_user_profiles_current_lon_range",
    ),
    CheckConstraint(
        "birthday_lat IS NULL OR (birthday_lat >= -90 AND birthday_lat <= 90)",
        name="ck_user_profiles_birthday_lat_range",
    ),
    CheckConstraint(
        "birthday_lon IS NULL OR (birthday_lon >= -180 AND birthday_lon <= 180)",
        name="ck_user_profiles_birthday_lon_range",
    ),
```

### 3.3. Pydantic-схемы (`apps/api/app/schemas/profile.py`)

Новый тип `LocationData`:

```python
class LocationData(CamelModel):
    city: str | None = Field(None, max_length=200)
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    tz: str | None = None

    @model_validator(mode="after")
    def _check_lat_lon_pair(self) -> "LocationData":
        if (self.lat is None) ^ (self.lon is None):
            raise ValueError("lat and lon must be set together")
        return self
```

Расширить `ProfileRead`:

```python
class ProfileRead(CamelModel):
    user_id: UUID
    first_name: str | None = None
    birth: BirthData
    current_location: LocationData | None = None
    birthday_location: LocationData | None = None
```

Расширить `ProfileWrite`:

```python
class ProfileWrite(CamelModel):
    first_name: str | None = Field(None, max_length=120)
    birth: BirthData = Field(default_factory=BirthData)
    current_location: LocationData | None = None
    birthday_location: LocationData | None = None
```

### 3.4. API `_to_read` и `_to_update` (`apps/api/app/api/profile.py`)

```python
from decimal import Decimal as D

def _loc_to_data(profile: UserProfile, prefix: str) -> LocationData | None:
    city = getattr(profile, f"{prefix}_city")
    lat = getattr(profile, f"{prefix}_lat")
    lon = getattr(profile, f"{prefix}_lon")
    tz = getattr(profile, f"{prefix}_tz")
    if city is None and lat is None:
        return None
    return LocationData(
        city=city,
        lat=float(lat) if isinstance(lat, D) else lat,
        lon=float(lon) if isinstance(lon, D) else lon,
        tz=tz,
    )

def _to_read(profile: UserProfile) -> ProfileRead:
    return ProfileRead(
        user_id=profile.user_id,
        first_name=profile.first_name,
        birth=BirthData(
            birthday=profile.birthday,
            birth_time=profile.birth_time,
            birth_city=profile.birth_city,
            birth_lat=float(profile.birth_lat) if isinstance(profile.birth_lat, D) else profile.birth_lat,
            birth_lon=float(profile.birth_lon) if isinstance(profile.birth_lon, D) else profile.birth_lon,
            birth_tz=profile.birth_tz,
        ),
        current_location=_loc_to_data(profile, "current"),
        birthday_location=_loc_to_data(profile, "birthday"),
    )
```

В `update_profile` — обработка новых полей:

```python
def _apply_location(profile: UserProfile, loc: LocationData | None, prefix: str) -> None:
    """Записать LocationData в колонки profile по префиксу (current/birthday)."""
    if loc is None:
        return
    setattr(profile, f"{prefix}_city", loc.city)
    setattr(profile, f"{prefix}_lat", D(str(loc.lat)) if loc.lat is not None else None)
    setattr(profile, f"{prefix}_lon", D(str(loc.lon)) if loc.lon is not None else None)
    setattr(profile, f"{prefix}_tz", loc.tz)
```

### 3.5. Контракты (`scripts/contracts/export_openapi.py`)

Добавить `LocationData` в `_TOP_LEVEL_NAMES` (рядом с `ProfileRead`, `ProfileWrite`):

```python
_TOP_LEVEL_NAMES: tuple[str, ...] = (
    ...
    "ProfileRead",
    "ProfileWrite",
    "LocationData",  # НОВОЕ
    ...
)
```

После — запустить `pnpm contracts:generate`.

### 3.6. Фронтенд — онбординг (`components/onboarding/onboarding-flow.tsx`)

Сейчас `finish()` отправляет только `birth`. Нужно добавить:

```typescript
await updateProfile({
  birth: {
    birthday,
    birthTime,
    birthCity: birthPlaceStr,
    birthLat: birthPlaceCity?.lat ?? undefined,
    birthLon: birthPlaceCity?.lon ?? undefined,
    birthTz: birthPlaceCity?.timezone ?? undefined,
  },
  currentLocation: effectiveCurrentCity
    ? {
        city: `${effectiveCurrentCity.name}, ${effectiveCurrentCity.country}`,
        lat: effectiveCurrentCity.lat,
        lon: effectiveCurrentCity.lon,
        tz: effectiveCurrentCity.timezone,
      }
    : null,
  birthdayLocation: effectiveBirthdayCity
    ? {
        city: `${effectiveBirthdayCity.name}, ${effectiveBirthdayCity.country}`,
        lat: effectiveBirthdayCity.lat,
        lon: effectiveBirthdayCity.lon,
        tz: effectiveBirthdayCity.timezone,
      }
    : null,
})
```

### 3.7. Фронтенд — профиль (`components/profile/profile-screen.tsx`)

Файл уже показывает `currentCity` и `birthdayCity` — но из `localStorage`. После подключения API:

1. `useProfile()` возвращает данные из `GET /api/profile`, включая `currentLocation` и `birthdayLocation`.
2. `ProfileScreen` рендерит `currentLocation.city` / `birthdayLocation.city` вместо `profile.currentCity` (из localStorage).
3. При редактировании (`EditSheet` с `CityPicker`) — `onSave` вызывает `updateProfile()` с `currentLocation` / `birthdayLocation`.

### 3.8. `today_service.py` — использовать `current_tz`

```python
# БЫЛО (строка 137):
target_tz=profile.birth_tz or "UTC",  # W-3.4: use birth_tz as current_tz (deferred)

# СТАЛО:
target_tz=profile.current_tz or profile.birth_tz or "UTC",
```

## 4. Инварианты

1. **lat/lon всегда парой**: если передан `lat`, должен быть `lon`, и наоборот. Валидатор на уровне Pydantic (`LocationData._check_lat_lon_pair`) и CheckConstraint на уровне БД.
2. **Обратная совместимость**: все 8 новых колонок `nullable`. Миграция заполняет их из `birth_*`. API возвращает `null` если не заполнено.
3. **Fallback-цепочка**: если `current_lat`/`current_lon` = `null`, потребитель (today_service, horary_service) fallback на `birth_lat`/`birth_lon`. Аналогично для timezone: `current_tz or birth_tz or "UTC"`.
4. **Координаты — опциональны**: пользователь может не указать текущий город. Тогда `current_location = null` — это допустимо.
5. **Data migration**: при `upgrade()` все существующие пользователи получают `current_* = birth_*` и `birthday_* = birth_*`. Это корректно: «живу там же» и «ДР там же» — значения по умолчанию в онбординге.
6. **Wire format**: все новые поля приходят на фронт в camelCase (`currentLocation`, `birthdayLocation`, `currentCity`, `currentLat`, `currentLon`, `currentTz`). Это обеспечивается `CamelModel.alias_generator = to_camel`.

## 5. Порядок реализации

| #  | Файл                                                       | Что                                                         |
|----|------------------------------------------------------------|-------------------------------------------------------------|
| 1  | `apps/api/alembic/versions/0010_add_profile_locations.py` | Миграция: 8 колонок + data copy + constraints               |
| 2  | `apps/api/app/db/models.py`                               | +8 колонок + 4 CheckConstraint в UserProfile                |
| 3  | `apps/api/app/schemas/profile.py`                          | +LocationData, расширить ProfileRead/Write                   |
| 4  | `apps/api/app/api/profile.py`                              | `_to_read` + `_apply_location` для новых полей              |
| 5  | `apps/api/app/services/profile_service.py`                | Обработка current_location/birthday_location в update        |
| 6  | `scripts/contracts/export_openapi.py`                      | +LocationData в _TOP_LEVEL_NAMES                            |
| 7  | `pnpm contracts:generate`                                  | Регенерация _generated.ts                                    |
| 8  | `packages/contracts/profile.ts`                            | Shim-реэкспорт LocationData (если нужно)                     |
| 9  | `components/onboarding/onboarding-flow.tsx`                | Отправка current_location/birthday_location в updateProfile |
| 10 | `hooks/use-profile.ts` или эквивалент                      | Подтягивание новых полей из API, мерж с localStorage        |
| 11 | `components/profile/profile-screen.tsx`                     | Показ current_location/birthday_location из API             |
| 12 | `components/profile/edit-sheet.tsx`                        | Редактирование новых location-полей (CityPicker)             |
| 13 | `apps/api/app/services/today_service.py`                   | Использовать `current_tz` вместо `birth_tz`                 |
| 14 | `apps/api/tests/test_profile_endpoints.py`                 | Тесты CRUD с новыми полями                                  |

## 6. Связь с другими ТЗ

| ТЗ                                  | Зависимость                                                           |
|--------------------------------------|-----------------------------------------------------------------------|
| `16_Horary_questions_TZ.md`         | Хорар использует `current_lat`/`current_lon` для ASC хорарной карты  |
| `17_Natal_landing_and_generation_TZ.md` | Соляр использует `birthday_lat`/`birthday_lon` для соляр-карты   |
| `02_Today_screen.md`                | Today-сервис использует `current_tz` для транзитов вместо `birth_tz` |

## 7. Non-goals

- Не меняем онбординг-визард (шаги и UI остаются те же).
- Не меняем `CityPicker` (уже работает с `/api/geo/autocomplete`).
- Не добавляем геолокацию по IP или `navigator.geolocation` (для MVP пользователь вводит город вручную).
- Не добавляем автоматическое определение часового пояса на бэкенде (на фронте `/api/geo/timezone` уже есть).
- Не меняем `lib/contracts/profile.ts` (Zod-схема профиля на фронте) — она описывает локальный state онбординга и не совпадает с API-контрактом. Синхронизация произойдёт при имплементации.