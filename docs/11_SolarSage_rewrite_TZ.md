---
id: doc-11-solarsage-svc
status: planned
wave: W-SOLARSAGE-SVC
last_review: 2026-05-25
---
# ТЗ: переделка SolarSage CLI-скрипта в HTTP-сервис (sidecar)

Версия: 0.1
Артефакты на входе:
- `apps/solarsage/collect_solarsage_western_deep.py` — текущий CLI-скрипт (вызывает внешний Swiss Ephemeris бинарник через subprocess, дампит JSON в файл).
- `apps/solarsage/sample_params.json` — пример выходного JSON с натальной картой (raw layers).
- `docs/04_SolarSage_нормализация_скоринг_кеширование.md` — контракт нормализации.
- `docs/05_API_contracts_и_TodayPayload.md` — что от sidecar-а ждёт основной API.
- `docs/07_Backend_architecture_draft.md` — место sidecar-а в архитектуре.

Цель: убрать оркестрацию через файлы и subprocess, превратить SolarSage в long-running HTTP-сервис (sidecar), к которому ходит наш FastAPI `apps/api`. Никакого CLI наружу, никакой записи в `tmp/`.

---

## 1. Контракт сервиса

Запуск: `uvicorn solarsage.app:app --host 127.0.0.1 --port 18091` (только loopback, никогда не публикуется наружу через nginx).

Базовый префикс: `/v1`.

### 1.1 `GET /v1/health`
Ответ: `{ "ok": true, "version": "<git_sha>", "ephemeris_path": "/opt/sweph/ephe", "calculation_version": "ss-1.0.0" }`.
Возвращает `200` только если эфемериды загрузились и пробный расчёт SUN на `now` отработал. Иначе `503`.

### 1.2 `POST /v1/natal`
Назначение: посчитать натальную карту один раз при создании/изменении профиля. Кешируется на стороне `apps/api`.

Запрос:
\`\`\`json
{
  "birth": {
    "date": "1980-10-30",
    "time": "19:50",
    "timezone": "Europe/Moscow",
    "latitude": 67.9387,
    "longitude": 32.9241,
    "place_name": "Мончегорск"
  },
  "options": {
    "house_system": "auto",          // "auto" | "WHOLE_SIGN" | "PLACIDUS" | "KOCH" | "EQUAL"
    "high_lat_threshold": 60.0,
    "include_layers": ["natal", "vargas", "dignities", "aspects", "fixed_stars"]
  }
}
\`\`\`

Ответ: тот же `raw.natal` блок, что лежит в `sample_params.json`, плюс meta:
\`\`\`json
{
  "schema_version": "ss.natal.v1",
  "calculation_version": "ss-1.0.0",
  "house_system_used": "WHOLE_SIGN",
  "house_system_policy": "auto_high_latitude_abs_lat_ge_60",
  "natal": { ... },                  // как сейчас в sample_params.json -> raw.natal.value
  "vargas": { ... },
  "dignities": { ... },
  "aspects": { ... },
  "fixed_stars": { ... }
}
\`\`\`

Никаких файлов не пишет.

### 1.3 `POST /v1/transits`
Назначение: посчитать положение неба и аспекты к натальной карте на конкретную дату/диапазон. Это основной endpoint для генерации Today.

Запрос:
\`\`\`json
{
  "natal": { ... },                  // ровно тот блок, что вернул /v1/natal (передаётся целиком, чтобы sidecar был stateless)
  "target": {
    "date": "2026-04-16",
    "timezone": "Europe/Moscow",
    "mode": "day"                    // "day" | "instant" | "range"
  },
  "options": {
    "include_layers": ["transits", "aspects_to_natal", "moon_phase", "void_of_course", "retrogrades", "ingresses"],
    "orb_profile": "default"
  }
}
\`\`\`

Ответ:
\`\`\`json
{
  "schema_version": "ss.transits.v1",
  "calculation_version": "ss-1.0.0",
  "target": { "date": "2026-04-16", "tz": "Europe/Moscow", "jd_ut_start": ..., "jd_ut_end": ... },
  "transits": { "planets": [ ... ] },
  "aspects_to_natal": [ { "transit": "MARS", "natal": "SUN", "type": "SQUARE", "orb": 1.42, "applying": true, "exact_at": "2026-04-16T11:23:00Z" } ],
  "moon": { "phase": "waxing_gibbous", "illumination": 0.78, "void_of_course": { "is_voc": false, "next_ingress": "..." } },
  "retrogrades": [ { "planet": "MERCURY", "is_retrograde": true, "since": "...", "until": "..." } ],
  "ingresses": [ { "planet": "VENUS", "from_sign": "Aries", "to_sign": "Taurus", "at": "..." } ]
}
\`\`\`

### 1.4 `POST /v1/range`
То же, что `/v1/transits` но для диапазона дат (для календаря). Возвращает массив дневных снимков. Лимит — максимум 92 дня за один запрос (на 3 месяца календаря).

### 1.5 Ошибки
Единый формат:
\`\`\`json
{ "error": { "code": "EPHEMERIS_MISSING", "message": "...", "details": {} } }
\`\`\`
Коды: `BAD_INPUT`, `EPHEMERIS_MISSING`, `HIGH_LATITUDE_FALLBACK`, `INTERNAL`.

---

## 2. Что выкинуть из текущего скрипта

В `collect_solarsage_western_deep.py` сейчас:
- argparse, чтение/запись файлов, `subprocess` к внешнему бинарю, `tempfile`, `urllib`.
- логика «собрать всё в один большой JSON dump».

Выкинуть всё, что относится к CLI и файлам. Оставить только чистые функции расчёта.

## 3. Что оставить и куда положить

Разнести текущий монолит на модули:

\`\`\`
apps/solarsage/
├── pyproject.toml
├── Makefile
├── solarsage/
│   ├── __init__.py
│   ├── app.py                  # FastAPI: роуты /v1/health, /v1/natal, /v1/transits, /v1/range
│   ├── settings.py             # EPHEMERIS_PATH, HOST, PORT, LOG_LEVEL (из env)
│   ├── core/
│   │   ├── ephemeris.py        # загрузка эфемерид, обёртка над pyswisseph (вместо subprocess)
│   │   ├── time.py             # date+time+tz -> jd_ut, обратные конверсии
│   │   ├── houses.py           # выбор дома + auto-fallback на WHOLE_SIGN при |lat|>=60
│   │   ├── planets.py          # позиции планет, скорости, ретро
│   │   ├── aspects.py          # MAJOR_ASPECT_DEFS, PLANET_ORBS, applying/separating, exact_at
│   │   ├── vargas.py           # D1..D12
│   │   ├── dignities.py
│   │   ├── fixed_stars.py
│   │   ├── moon.py             # фаза, void-of-course
│   │   ├── retrogrades.py
│   │   └── ingresses.py
│   ├── schemas/
│   │   ├── requests.py         # pydantic модели запросов
│   │   └── responses.py        # pydantic модели ответов (= TS-контракты sidecar)
│   └── services/
│       ├── natal_service.py    # компонует natal-ответ
│       ├── transits_service.py # компонует transits-ответ
│       └── range_service.py
└── tests/
    ├── test_natal_vasiliy.py   # эталон: входы из sample_params.json -> совпадение по ключевым полям
    ├── test_transits.py
    └── test_high_lat_fallback.py
\`\`\`

## 4. Зависимости

`pyproject.toml`:
- `fastapi`, `uvicorn[standard]`, `pydantic>=2`
- `pyswisseph` (заменяет внешний бинарник + `subprocess`; ставится из PyPI, тянет за собой эфемериды отдельно)
- `python-dateutil`, `tzdata`
- dev: `pytest`, `httpx`, `ruff`, `mypy`

Эфемериды лежат на VDS в `/opt/sweph/ephe` (см. `apps/solarsage/Makefile` цель `ephemeris`). Путь читается из `SOLARSAGE_EPHE_PATH`.

## 5. Конфиг

`solarsage/settings.py` через pydantic-settings:
- `SOLARSAGE_HOST` (default `127.0.0.1`)
- `SOLARSAGE_PORT` (default `18091`)
- `SOLARSAGE_EPHE_PATH` (обязательно)
- `SOLARSAGE_LOG_LEVEL` (default `INFO`)
- `SOLARSAGE_CALCULATION_VERSION` (берётся из git-sha при сборке)

## 6. Версионирование

В каждом ответе:
- `schema_version` — версия именно этого payload (`ss.natal.v1`, `ss.transits.v1`).
- `calculation_version` — версия движка SolarSage целиком (`ss-1.0.0`).

Изменили орбисы / правила домов / добавили слой → bump `calculation_version`. `apps/api` хранит этот ключ в кеше и инвалидирует Today/Calendar при несовпадении.

## 7. Что должен делать `apps/api` (для понимания границы)

- Хранит `natal_raw` в БД (одна запись на пользователя; `ON UPDATE` пересчёт).
- При генерации Today: `POST /v1/transits` с `natal` из БД + `target.date`.
- Кеширует результат в Redis по ключу `today:{user_id}:{date}:{calculation_version}` на 24ч.
- Sidecar НЕ ходит в БД, НЕ знает про пользователей, НЕ нормализует и НЕ скорит. Нормализация и скоринг — на стороне `apps/api/app/services/normalization.py` и `scoring.py` (см. `docs/04`).

## 8. Тестовый чек-лист (DoD)

- [ ] `pytest` зелёный, в т.ч. эталонный тест: вход из `sample_params.json` → ответ `/v1/natal` совпадает с `raw.natal.value` по `planets[*].longitude` (точность 1e-6) и `house` (точное равенство).
- [ ] `GET /v1/health` отдаёт 200 после `systemctl start solarsage`.
- [ ] При |lat|>=60 и `house_system: "auto"` в ответе `house_system_used == "WHOLE_SIGN"`.
- [ ] `/v1/range` на 92 дня отрабатывает < 3 сек на проде.
- [ ] Сервис не открывает 0.0.0.0; в `infra/systemd/solarsage.service` указан bind на `127.0.0.1`.
- [ ] При отсутствии эфемерид — `503` с `EPHEMERIS_MISSING`, не падение процесса.
- [ ] `apps/api` ходит только по HTTP, никаких subprocess, никаких файлов между сервисами.

## 9. Миграция со старого скрипта

1. Сохранить текущий `collect_solarsage_western_deep.py` под именем `_legacy_collect.py` в этой же папке для справки (потом удалить).
2. Перенести из него в `solarsage/core/*` чистые функции (без I/O): расчёт планет, аспектов, варг, достоинств, фиксированных звёзд.
3. Все `subprocess.run([...])` заменить на прямые вызовы `swisseph` (`import swisseph as swe`).
4. Убрать чтение/запись JSON-файлов; вход — pydantic-модели, выход — pydantic-модели.
5. Завести pytest с эталоном из `sample_params.json`.
6. Завести `infra/systemd/solarsage.service` (уже есть в скелете) и проверить `systemctl status solarsage`.

## 10. Не входит в этот скрипт (делается в `apps/api`)

- Нормализация (приведение к 0..1 + категории).
- Скоринг дня.
- Шаблоны/LLM-генерация.
- Кеш в Redis.
- HMAC Telegram, юзеры, доступ.

Sidecar делает только астрономию.

---

## 11. Reference Collector Status (W-3.0)

**GRACE Wave:** W-3.0 (PHASE-3-SIDECAR)  
**Module:** M-SOLARSAGE-REFERENCE-COLLECTOR

The existing `collect_solarsage_western_deep.py` is declared **reference-only** as of W-3.0.

### Purpose

- Generate golden fixtures for parity tests
- Serve as coverage/reference for future sidecar implementation (W-3.1 → W-3.4)
- **NOT used in product runtime**

### Golden Fixtures

Located in `apps/solarsage/tests/fixtures/`:

- `vasiliy_2026-05-30.json` — Controller-approved chart (Vasiliy)
  - Birth: 1980-10-30 19:50 Europe/Moscow (67.9387°N, 32.9241°E, Murmansk)
  - Target: 2026-05-30 (age 45)
  - House System: WHOLE_SIGN (auto-selected due to high latitude ≥60°)
  - Raw Layers: 30 layers (all successful)

- `test_user_2026-06-15.json` — Additional test case (normal latitude)
  - Birth: 1990-01-15 14:30 Europe/Moscow (55.7558°N, 37.6173°E, Moscow)
  - Target: 2026-06-15 (age 36)
  - House System: PLACIDUS (auto-selected due to normal latitude <60°)
  - Raw Layers: 30 layers (all successful)

### Parity Gate

Future sidecar implementation (W-3.1 → W-3.4) must match these fixtures within declared tolerances:

- **Planets longitudes:** ±1e-6 deg
- **Houses cusps:** ±1e-6 deg
- **Aspects orbs:** ±1e-4 deg
- **Timestamp fields:** Excluded from comparison

### Parity Tests

Run parity tests:

```bash
cd /opt/solarsage-astro
pytest apps/solarsage/tests/test_parity.py -v
```

Tests verify:
- Fixture existence and structure
- Natal planets longitudes and signs
- House cusps validity
- Special points (ASC, MC, DSC, IC, VERTEX, etc.)
- Major aspects structure and orbs
- House system selection (WHOLE_SIGN at high latitude, PLACIDUS at normal)
- Reproducibility (same input → same output)

### Reproducibility

If fixture generation finds reproducibility defects (e.g., non-deterministic output, timezone issues), the collector may be fixed. All other changes are frozen per W-3.0 freeze-scope.

### Coverage

Each fixture includes:

**Raw layers (30):**
- natal, natal_whole_sign, natal_placidus
- chart_wheel, dignity, bonification
- dispositors (modern/traditional)
- profection, lots, bounds, antiscia
- planetary_hours, heliacal, fixed_stars, midpoints
- aspect_patterns
- transit, progressions, solar_arc
- primary_directions, symbolic_directions
- solar_return, lunar_return
- lunar_phase (birth/target/year), eclipses
- firdaria, natal_report

**Derived layers:**
- element_balance, modality_balance, house_emphasis
- hemisphere_balance, quadrant_balance, angular_planets
- dispositor_chains, final_dispositor_frequency
- major_aspects_ranked, all_aspects_ranked
- special_points, special_point_major_aspects
- sphere_scores, lots, aspect_patterns
- antiscia, dignities, mutual_receptions, sect
- bonification, faces, planetary_hours
- heliacal_events, fixed_star_conjunctions, midpoints

### Verification Matrix

See `grace/verification-matrix.md` for the full parity gate specification:

- **S1:** Vasiliy golden chart and target date regenerate byte-stable normalized JSON except timestamp fields
- **S2:** A high-latitude chart uses the documented house-system fallback (WHOLE_SIGN at ≥60°)
- **S3:** Chiron/Nodes/Lilith/Vertex fixed-star and aspect coverage remains present after service split
