# M7 TZ: глобальная дедупликация why-строк между сферами + анти-попугай промпт

Дата: 2026-07-27
Phase / Wave: **W-TODAY-SPHERE-WHY-MODALS**, срез M7 (backend)
Modules: `M-API-SPHERE-WHY-BUILDER`, `M-API-TODAY-INTERPRETATION-SERVICE`, `M-API-LLM-SERVICE`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Проблема (живая генерация 2026-08-04)

- Одна и та же why-строка «Мечты и чуткость сталкиваются с правилами и
  сроками — работает сегодня» показана в work, money и sport: один фактор
  кормит топ-evidence нескольких сфер → копипаста в модалках.
- Story попугайничает строками фактов («ты отлично справляешься с
  самовыражением и целями») вместо жизненной сцены.

## 2. Goal

- Каждая why-строка показывается максимум в ОДНОЙ сфере — той, где её
  фактор сильнее всего (по strength исходного evidence). В остальных сферах
  берётся следующая уникальная кандидат-строка, иначе why уменьшается
  честно (вплоть до []).
- Story не копирует формулировки блока «Факты», а пересказывает их смысл
  через конкретную сцену.

## 3. Exact write scope

- `apps/api/app/services/sphere_why_builder.py` — добавить
  `build_sphere_why_items(evidence) -> list[WhyItem]` (WhyItem: line,
  pair_key, strength), `build_sphere_why` оставить строковой обёрткой над
  ним (обратная совместимость тестов).
- `apps/api/app/services/today_interpretation_service.py` — после
  формирования staged/details: глобальный проход дедупликации по строке
  (assign к max-strength сфере; проигравшие сферы берут следующего
  уникального кандидата из своих items; pair_key тоже считается
  дубликатом — одна пара планет = одна сфера).
- `apps/api/app/services/llm_service.py` — промпт: «Не копируй
  формулировки блока Факты дословно. Перескажи их смысл через конкретную
  сцену с маркером времени или места (утром, на встрече, в переписке,
  дома вечером)».
- `apps/api/tests/` — тесты билдера (items API) и дедуп-прохода.

## 4. Frozen / out-of-scope

- Контракт details {story, why[], advice}; row.text = advice.
- Порядок сфер, verdict, counts, scoring.
- Модель, число вызовов, дедлайны. Frontend.

## 5. Must-preserve

- attempt acceptance ≥9; details=None fallback; banned-жаргон reject.
- Детерминизм: одинаковый вход → одинаковый набор строк и назначение сфер.
- attempt без LLM (fallback rows) — details=None как сейчас.

## 6. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "sphere_why or concrete_advice or interpretation"
```

## 7. Expected evidence

- Вывод verification; пример: один конфликтный фактор, назначенный одной
  сфере (текстом в отчёте).

## 8. Escalation rule

Нужен файл вне §3 — стоп, доложить. Ничего не коммить и не пушить.
