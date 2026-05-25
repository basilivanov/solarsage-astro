---
id: doc-13-evening
status: planned
wave: W-EVENING
last_review: 2026-05-25
---
## docs/13 — Evening CheckIn и Yesterday Echo

Цель: продуктовая петля «вечером отметил → утром получил closure». Это то, что превращает приложение из «гороскоп на сегодня» в «дневник, который тебя знает». И именно это даёт эффект «чекни вчерашний — охуеешь».

---

### 1. Контур

```
20:00 локального времени  →  пуш/баннер «как прошёл день?»
                          →  POST /api/checkin  { mood, accuracy, note? }
                          ↓
                          сохраняем в evening_checkins
                          ↓
утро следующего дня       →  GET /api/day/:date
                          →  composer подтягивает вчерашний checkin
                          →  TodayPayload.yesterdayEcho.closureText
                          ↓
фронт: блок «вчера ты сказал X — сегодня поэтому Y»
```

Closure-фраза — главный wow-момент: пользователь вчера сам написал «чувствовал тревогу», а утром видит «вчера Луна шла в квадрате к Сатурну, поэтому давило; сегодня она ушла — должно отпустить».

---

### 2. Схема БД

```sql
CREATE TABLE evening_checkins (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date         DATE   NOT NULL,                  -- день, ПРО который чекин (не дата создания)
  mood         SMALLINT NOT NULL,                -- 1..5
  accuracy     SMALLINT,                         -- 1..5, насколько прогноз попал
  energy       SMALLINT,                         -- 1..5, опц.
  tags         TEXT[]   DEFAULT '{}',            -- ["work_win", "argument", "tired"]
  note         TEXT,                             -- свободный текст, ≤ 500 симв
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, date)
);

CREATE INDEX idx_checkins_user_date ON evening_checkins(user_id, date DESC);
```

Один чекин на пользователя на дату. Повторный POST — upsert.

---

### 3. API контракты

#### POST /api/checkin

```ts
// request
{
  date: string;            // ISO yyyy-mm-dd, по умолчанию = сегодня в TZ пользователя
  mood: 1 | 2 | 3 | 4 | 5;
  accuracy?: 1 | 2 | 3 | 4 | 5;
  energy?: 1 | 2 | 3 | 4 | 5;
  tags?: string[];         // из закрытого списка (см. ниже)
  note?: string;           // ≤ 500 символов
}

// response
{ ok: true; checkin: EveningCheckin }
```

Закрытый список тегов v1:
`work_win, work_fail, money_in, money_out, argument, support, tired, energetic, anxious, calm, focused, scattered, lucky, unlucky, social, alone, sport, sleep_bad, sleep_good`.

#### GET /api/checkin/:date

Возвращает чекин или 404.

#### GET /api/checkin/yesterday

Шорткат для composer-а. Возвращает чекин за вчера в TZ пользователя или null.

---

### 4. Composer: yesterdayEcho

В `services/today_composer.py` после нормализации/скоринга/microcopy:

```
1. yesterday_checkin = checkin_repo.get(user_id, yesterday_in_user_tz)
2. yesterday_events  = day_cache.get(user_id, yesterday)?.normalized_events
3. closure = yesterday_service.build_closure(yesterday_checkin, yesterday_events, today_events)
4. payload.yesterdayEcho = closure  (или None)
```

Логика `build_closure`:

- Если чекина нет → `yesterdayEcho = None`. Не выдумываем.
- Если есть, берём 1 событие вчера с самым высоким весом, которое тематически совпадает с тегами/настроением чекина.
- Сравниваем с сегодняшним: ушло / усилилось / трансформировалось.
- Берём фразу из словаря закрытий (`microcopy.v1.json` секция `closures`) по ключу `(yesterday_polarity, today_polarity, transition)`.

Примеры closure_text:
- `"Вчера давила квадратура Луна-Сатурн — ты отметил тревогу. Сегодня Луна ушла в трин, должно отпустить к обеду."`
- `"Вчера ты поймал волну (Венера в трине к Юпитеру) и сам это почувствовал. Сегодня волна стихает, не жди повтора — фиксируй."`

---

### 5. TodayPayload — расширение

```ts
export type YesterdayEcho = {
  hadCheckin: boolean;
  mood?: 1 | 2 | 3 | 4 | 5;
  accuracy?: 1 | 2 | 3 | 4 | 5;
  closureText: string;        // 1–2 предложения, готовый текст
  transition: "released" | "intensified" | "shifted" | "continued";
};

// в TodayPayload:
yesterdayEcho?: YesterdayEcho;
```

Фронт показывает блок только если `yesterdayEcho?.hadCheckin === true`. Иначе показывает CTA «отметить вчерашний день» (опц., если позже 12:00 и чекина за вчера нет).

---

### 6. Уведомления

- 20:00 локального времени → пуш «как прошёл день?» с deeplink на `/checkin?date=today`.
- Cron в воркере (`apps/api/app/workers/`): раз в час пробегает по пользователям, у кого `tz_offset` = текущему часу `20:00 - now`.
- Anti-spam: не больше 1 пуша в день. Если пользователь уже сделал чекин — не шлём.

---

### 7. Безопасность и приватность

- `note` — свободный текст, может содержать персональное. Не логируем в общий лог, не шлём в LLM без явного согласия.
- В payload composer-у можно отдавать только `mood/accuracy/tags`, без `note`, если `prompt_version` не помечен как «note-aware».
- Удаление аккаунта → каскадно удаляются чекины (`ON DELETE CASCADE`).

---

### 8. DoD

- [ ] Миграция alembic: таблица `evening_checkins`.
- [ ] Роутер `apps/api/app/api/checkin.py`: POST/GET/yesterday.
- [ ] `services/yesterday_service.py`: `build_closure` + покрытие тестами на 6 кейсов (released/intensified/shifted/continued × had_data/no_data).
- [ ] `today_composer` подмешивает `yesterdayEcho` в payload, не ломая ответ если чекина нет.
- [ ] Воркер шлёт вечерние пуши по TZ.
- [ ] Фронт: экран чекина (форма с моодом 1–5, чипами тегов, опц. note); блок «Вчера» на главной показывается только при наличии closure.
- [ ] Контракт `packages/contracts/today.ts` обновлён, `YesterdayEcho` экспортируется.
