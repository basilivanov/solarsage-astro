# D1_TZ: относительный статус дня (персональный базлайн) — backend

## 1. Packet title
Relative day status: статус дня от персонального базлайна (z-score по последним 14 дням) + абсолютные рамки + гистерезис + холодный старт. Поля в TodayPayload для zone-индикатора.

## 2. Phase / Wave
W-DAY, relative status. Контекст: 14/14 дней у владельца «steady» — абсолютные пороги не дают разнообразия. Решение владельца: модель Whoop (z к собственному базлайну) + абсолютные гварды + гистерезис + fallback.

## 3. Modules
- `apps/api/app/services/day_relative_status.py` (новый модуль)
- `apps/api/app/services/today_service.py` (интеграция: считать скоры, писать историю, выставить поля)
- `apps/api/app/db/models.py` (таблица истории скоров) + alembic миграция
- `apps/api/app/schemas/day.py` (поля ответа)

## 4. Goal

### 4.1. Хранилище истории
Таблица `day_score_history` (migration 0027): `user_id, date, support_score float, tension_score float, PRIMARY KEY (user_id, date)`. Записывать при каждом построении payload (upsert; только скоры, без payload — маленькая таблица).

### 4.2. Относительный статус (`day_relative_status.py`)
Вход: support/tension сегодня + история (до 14 последних дат ДО сегодняшней).
- История < 5 дат → `mode="absolute"`, статус по текущей формуле (`_compute_day_status_v2`) — fallback.
- История ≥ 5 дат → `mode="relative"`:
  - baseline mean/std (std floor 0.5, чтобы не делить на ~0).
  - `z_support = (support − mean_s)/std_s`, `z_tension = (tension − mean_t)/std_t`.
  - `z ≥ 0.75` для tension два дня подряд (гистерезис по истории) → «напряжённее обычного»; `z_support ≥ 0.75` два подряд → «легче обычного»; иначе «обычный день».
  - **Абсолютные рамки**: если текущая абсолютная формула даёт `tense` → статус «тяжёлый день» независимо от z; если `supportive` → «сильный день». (Экстремумы побеждают относительную подпись.)
- Выход: `{mode, status ("usual"|"softer"|"tenser"|"hard"|"strong"), z_support, z_tension, baseline: {support_mean, support_std, tension_mean, tension_std, days: n}}`.
- Zone-данные для UI: `band = [mean−std, mean+std]` (clip ≥0), `marker` = положение сегодняшнего score в 0..100 внутри [0, band_high*1.5].

### 4.3. Интеграция в today_service
- После вычисления support/tension: upsert в `day_score_history`, вызвать `compute_relative_status`, проставить поля в TodayPayload: `relative_status` (объект выше). НЕ ломать существующий `day_status` (v2 остаётся).
- Тексты подписей (детерминированные): usual → «Обычный день», softer → «Легче, чем обычно», tenser → «Напряжённее обычного», hard → «Тяжёлый день», strong → «Сильный день».

## 5. Exact write scope
- `apps/api/app/services/day_relative_status.py` (новый)
- `apps/api/app/services/today_service.py`
- `apps/api/app/db/models.py` (только таблица)
- `apps/api/alembic/versions/0027_day_score_history.py` (новая, один parent)
- `apps/api/app/schemas/day.py`
- `apps/api/tests/test_day_relative_status.py` (новый)
- `apps/api/tests/test_today_service.py` (обновить при необходимости)

## 6. Frozen / Out of scope
- Frontend (D2), LLM-тексты, scoring formula (v2 не трогать), sidecar.
- Миграция существующих day_status в UI (D2).

## 7. Must-preserve invariants
- `day_status` (v2) не меняется; новые поля additive.
- Всё детерминировано: никаких LLM-вызовов на этом пути.
- История пишется один раз на (user,date) — upsert идемпотентен.
- ruff/mypy/grace_lint зелёные; полный pytest зелёный.

## 8. Verification commands
```bash
cd apps/api && source .venv/bin/activate
python -m alembic upgrade head
python -m pytest tests/test_day_relative_status.py tests/test_today_service.py -q
ruff check app/
mypy app/services/day_relative_status.py
```
Тесты: z-расчёт, std floor, гистерезис 2-дня, absolute override (tense→hard, supportive→strong), cold-start fallback, zone marker clip.

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок; `alembic heads` = 0027.

## 10. Escalation rule
Нужен scoring formula / frontend / миграция данных → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
