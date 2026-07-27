# S2 TZ: синтез дня mainAdvice — «Главное» из фактов дня, не копипаста топ-сферы

Дата: 2026-07-28
Phase / Wave: **W-DAY-HONEST-UNAVAILABLE**, срез S2
Modules: `M-API-LLM-SERVICE`, `M-API-TODAY-INTERPRETATION-SERVICE`, `M-SCHEMAS-TODAY`, `M-ACTIVATION-EVIDENCE-CARD`
Роль: кодер. Ничего не коммить и не пушить — коммит делает ревьюер.

## 1. Проблема

«Главное:» в карточке дня — дословный advice сферы rank=1 (дубль модалки
этой сферы, механический выбор). Нужен настоящий синтез дня: одна фраза,
написанная из детерминированных фактов дня, без fallback (S1).

## 2. Дизайн (нормативно)

`daySummary.mainAdvice: str | None` — одна фраза ≤120 символов на «ты».

Детерминированный вход (только это, ничего больше):

1. `dayStatus` + support/tension из valence breakdown;
2. топ-сфера: tense-день → max tensionScore; supportive → max supportScore;
   steady → max total; (tie → canonical key asc);
3. её детерминированная why-строка из `sphere_why_builder`
   (может быть пустой);
4. title fast-горизонта, если есть.

LLM (тот же ОДИН вызов на 12 сфер — добавить ключ `day_main` в структурный
JSON, не новый вызов) пишет фразу: суть дня + одно действие, без
астротерминов, без фатализма, без копирования why-строки дословно.

Валидация: banned-жаргон + длина + непустота. Невалидно/нет LLM →
`mainAdvice = None` (честная недоступность; фронт скрывает блок «Главное»).

## 3. Exact write scope

- `apps/api/app/services/llm_service.py` — JSON-схема ответа += `day_main`
  (string); промпт: правила для day_main из блока «Факты дня».
- `apps/api/app/services/today_interpretation_service.py` — сбор фактов
  (статус, топ-сфера, why, fast title), применение/валидация day_main в
  `daySummary.mainAdvice`; reject-лог по S1-правилам при невалидности.
- `apps/api/app/schemas/today.py` — `DaySummaryBlock.mainAdvice: str | None`.
- `npm run contracts:generate` + `lib/contracts/today.ts` — регенерация.
- `components/today/activation-evidence-card.tsx` — «Главное» из
  `daySummary.mainAdvice` (новый prop через payload.daySummary), скрытие
  блока при None; ranked-строки НЕ трогать.
- Тесты backend (apply/validation) + frontend (render/hide).

## 4. Frozen / out-of-scope

- Новые LLM-вызовы (только расширение существующего), модель, дедлайны.
- Структура ranked-строк, «Все сферы дня», why-модалки.
- Число/порядок остальных блоков экрана.

## 5. Must-preserve

- attempt acceptance ≥9; детерминированный why (M6/M7) не трогать.
- `mainAdvice=None` → блок «Главное» полностью скрыт (нет пустого shell).
- Banned-валидатор по S1 (reject, не перезапись).

## 6. Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q -k "concrete_advice or main_advice or interpretation"
npx vitest run __tests__/components/ActivationEvidenceCard.personal.test.tsx
```

## 7. Expected evidence

- Файлы, вывод verification, пример mainAdvice из живого контекста
  (текстом).

## 8. Escalation rule

Нужен файл вне §3 / второй LLM-вызов — стоп, доложить. Ничего не коммить
и не пушить.
