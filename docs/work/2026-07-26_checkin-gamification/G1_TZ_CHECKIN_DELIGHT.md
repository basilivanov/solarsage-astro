# G1_TZ: чекин — «ответ засчитан» + геймификация серии

## 1. Packet title
Checkin delight: после ответа — благодарность и «ответ засчитан» с серией; streak-геймификация (карточка чекина + блок в профиле).

## 2. Phase / Wave
Checkin gamification. Контекст: пуш от бота в 20:15 (прод) → пользователь открывает чекин → сейчас после ответа только микро-тост. Backend готов полностью: `GET /api/checkin/metrics` отдаёт `total_checkins, current_streak, longest_streak, average_mood, distributions`; `createCheckin` возвращает `streak`.

## 3. Modules
- `components/checkin/checkin-screen.tsx` (post-submit состояние)
- `components/today/today-screen.tsx` или отдельная карточка-напоминание (streak chip)
- `components/profile/profile-screen.tsx` + новый `components/profile/checkin-stats-card.tsx`
- `lib/api/checkin.ts` (клиент metrics, если нет)

## 4. Goal

### 4.1. Post-submit подтверждение (вместо тоста)
После успешного `createCheckin` — заменить тост полноценным состоянием в чекин-экране:
- «Спасибо ✓ Ответ засчитан» (дружелюбно, по-человечески);
- серия крупно: «{streak} {день/дня/дней} подряд»;
- прогресс до ближайшего milestone (3/7/14/30): «до недели — ещё {n}» (или «milestone достигнут 🎉» при точном попадании);
- кнопка «Понятно»/закрытие → прежний flow (onComplete).
Сохранить повторное редактирование (existing checkin edit → тот же апдейт-путь).

### 4.2. Streak chip на карточке чекина
На напоминании/карточке чекина на today-экране: если current_streak > 0 — мелкий чип «🔥 {n} подряд» (подгрузить metrics лениво с экрана; без лишнего запроса если уже есть в payload — решить по месту, документировать выбор).

### 4.3. CheckinStatsCard в профиле
Новый `components/profile/checkin-stats-card.tsx` (по образцу horary-card):
- текущая серия (🔥 N), лучшая серия, всего отчётов;
- milestone-бейджи 3/7/14/30: достигнутые — активные, будущие — приглушённые;
- `data-testid="checkin-stats-card"`.
Вставить в `profile-screen.tsx` рядом с credits-card.

## 5. Exact write scope
- `components/checkin/checkin-screen.tsx`
- `components/profile/checkin-stats-card.tsx` (новый)
- `components/profile/profile-screen.tsx`
- `components/today/today-screen.tsx` (только streak chip, минимально)
- `lib/api/checkin.ts` (metrics клиент если отсутствует)
- `__tests__/checkin/` (обновить/добавить)

## 6. Frozen / Out of scope
- Backend (metrics/стreak готовы), бот/пуш (прод-сторона), дизайн остальных экранов.
- Никаких новых кредитов/наград токенами (чистая UI-геймификация).

## 7. Must-preserve invariants
- data-testid контракты today/profile экранов.
- GRACE-разметка новых файлов; vitest зелёный; lint чист.

## 8. Verification commands
```bash
npx vitest run __tests__
pnpm run lint
```

## 9. Expected evidence
- `git diff --name-only` — только scope-файлы.
- Вывод проверок; скрин состояния «ответ засчитан» и карточки статистики.

## 10. Escalation rule
Нужен backend/бот scope → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
