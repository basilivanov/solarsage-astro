# M6 TZ: детерминированный why[] сфер из evidence + story на фактах

Дата: 2026-07-27
Phase / Wave: **W-TODAY-SPHERE-WHY-MODALS**, срез M6 (backend)
Modules: новый `M-API-SPHERE-WHY-BUILDER`, `M-API-TODAY-INTERPRETATION-SERVICE`, `M-API-LLM-SERVICE`, `M-API-LLM-CLAIM-VALIDATOR`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Проблема

LLM-генерированные `why[]` — вода («Поддержка в сфере денег связана с
гармонией в делах…»), галлюцинирует причины и ловит banned-жаргон.
При этом каждая сфера несёт до 3 структурированных evidence
(`ConcreteAdviceEvidence`: kind, planet, target_planet, aspect_type,
technique, technique_family, strength). Причинность — не LLM-территория:
`why[]` должен считаться детерминированно из evidence.

Живой пример evidence (work, 2026-08-04):
`Transit Venus sextile natal Uranus (orb 2.8)`, `Transit Sun semi_square
natal Venus (orb 3.3)`.

## 2. Goal

`details.why[]` — 1–2 строки, вычисленные детерминированно из топ-evidence
сферы, на человеческом русском, без единого астротермина и без имён планет.
LLM пишет только story/advice, опираясь на эти факты.

## 3. Дизайн why-строк (нормативно)

Маппинги (задать константами в новом модуле; для смыслов сверяться с
`PLANET_MEANINGS` в `apps/api/app/services/synastry_llm.py`):

- Функция планеты: Sun → «самовыражение и цели», Moon → «эмоции и привычки»,
  Mercury → «мысли и разговоры», Venus → «чувства и симпатии»,
  Mars → «действия и темп», Jupiter → «возможности и рост»,
  Saturn → «правила и сроки», Uranus → «перемены и свобода»,
  Neptune → «мечты и чуткость», Pluto → «глубокие изменения».
  Префикс `Transit_` / регистр / `natal` — нормализовать.
- Направление: conjunction/sextile/trine → «поддерживает»;
  square/opposition/quincunx/semi_square/sesquisquare → «сталкивается с».
- Масштаб: kind=="aspect" или technique_family=="transit" → «работает
  сегодня»; firdar/profection → «долгий фон»; return/progression →
  «текущий период»; неизвестно → без хвоста масштаба.

Шаблон строки:
`«{Функция source} {поддерживает|сталкивается с} {функцией target} — {масштаб}»`
Пример: «Чувства и симпатии поддерживают твои перемены и свободу — работает сегодня».

Правила: не более 2 строк (топ по strength, дедуп по паре планет); нет
имён планет, аспектов, орбов, домов, знаков в выводе; evidence без
планет/aspect — пропускать; пустой результат = `why: []` (честно).

## 4. Exact write scope

- `apps/api/app/services/sphere_why_builder.py` — **новый** чистый модуль
  `M-API-SPHERE-WHY-BUILDER` (build_sphere_why(evidence: list[dict]) -> list[str]).
- `apps/api/app/services/today_interpretation_service.py` — после применения
  attempt: `details.why` = вывод билдера из `row.evidence` (LLM-версия why
  игнорируется); deterministic даже при частичном attempt.
- `apps/api/app/services/llm_service.py` — промпт: убрать генерацию why из
  задачи (поле оставить в схеме для обратной совместимости, инструкция —
  возвращать `[]`); в контекст каждой сферы добавить блок «Факты (уже
  посчитано детерминированно)» со строками билдера; story обязана опираться
  на эти факты; story ≤ 2 предложений, одна конкретная сцена.
- `apps/api/app/services/llm_claim_validator.py` — добавить стемы в
  banned: «поддержк», «влияни», «гармони» (story/advice); существующие
  стемы не трогать.
- `apps/api/tests/` — новые unit-тесты билдера + обновление существующих
  этого контура.

## 5. Frozen / out-of-scope

- Контракт `details {story, why[], advice}` и `row.text = advice`.
- Scoring/valence/verdict (W2). Frontend (дедуп периода делает ревьюер).
- Число LLM-вызовов (один), модель, дедлайны.

## 6. Must-preserve

- attempt acceptance ≥9; details=None fallback; banned-жаргон reject.
- GRACE-разметка в новом и изменённых файлах; owned_tests в MODULE_MAP.

## 7. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "sphere_why or concrete_advice or claim_validator or interpretation"
```

## 8. Expected evidence

- Вывод verification; 3 примера why-строк билдера из живых evidence
  (текстом в отчёте).

## 9. Escalation rule

Нужен файл вне §4 / новые зависимости — стоп, доложить. Ничего не коммить
и не пушить.
