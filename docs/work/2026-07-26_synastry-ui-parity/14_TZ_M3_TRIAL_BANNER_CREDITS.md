# 14_TZ (M3): кнопка «Подписка» → /profile + карточка общих кредитов

## 1. Packet title
TrialBanner: мёртвая кнопка «Подписка» ведёт в профиль; в профиле — карточка общих кредитов (3 сервиса) с «осталось N», разбивкой и датой следующего бесплатного.

## 2. Context
- Кредиты ОБЩИЕ для horary/election/synastry (shared `HoraryCredit` wallet: weekly-free 1/нед + bonus + paid).
- `TrialBanner` (`components/monetization/trial-banner.tsx`, today-screen) — кнопка «Подписка» без onClick (мёртвая).
- `components/profile/horary-card.tsx` — уже показывает weeklyFree/nextWeeklyFreeAt/total, но подписан «Хорарные вопросы» (кредиты общие — подпись врёт).
- `profile-screen.tsx:177,195` — секция AccessCard + HoraryCard.
- `lib/profile-meta.ts` — `weeklyFreeAvailable`, `weeklyFreeExpiresAt`, `nextWeeklyFreeAt`, `bonusCredits`, `paidCredits` уже есть.

## 3. Goal

### 3.1. Кнопка «Подписка»
- `TrialBanner`: кнопка «Подписка» → `router.push('/profile#credits')`; type="button", aria-label «Перейти к подписке и кредитам».
- `profile-screen.tsx`: секция с карточками доступа/кредитов получает `id="credits"` (scroll-mt, чтобы не перекрывалось шапкой).

### 3.2. Карточка общих кредитов (rework `horary-card.tsx`)
- Заголовок секции: «Кредиты на разборы» (не «Хорарные вопросы» — общие для всех сервисов).
- Главная строка: «Осталось {total} {разборов/разбора/разбора}».
- Разбивка строками (все, что >0 или применимо):
  - «Бесплатный еженедельный: активен (до {weeklyFreeExpiresAt})» ИЛИ «Бесплатный еженедельный: потрачен»
  - «Следующий бесплатный: {nextWeeklyFreeAt}» (когда weekly потрачен)
  - «Бонусные: {bonusCredits}», «Платные: {paidCredits}»
- Подпись внизу мелко: «Общие кредиты для разборов дня, хорарных вопросов и синастрии» (или по факту сервисов, которые тратят wallet — проверить элективку: election тратит тот же wallet? если да — перечислить честно все три).
- Сохранить data-testid/структурный контракт если есть; добавить `data-testid="credits-card"`.

## 4. Exact write scope
- `components/monetization/trial-banner.tsx`
- `components/profile/horary-card.tsx`
- `components/profile/profile-screen.tsx`
- `__tests__/components/` (тест баннера/карточки если есть; иначе новый рядом по паттерну)

## 5. Frozen / Out of scope
- Backend (quota API уже отдаёт всё нужное), монетизация/paywall логика, подписка как продукт.
- Тексты макетов других экранов.

## 6. Must-preserve invariants
- data-testid="trial-banner" (если есть) и экранные контракты.
- Общий wallet не переименовывать в API-слое (только UI-тексты).
- Тесты зелёные.

## 7. Verification
```bash
npx vitest run __tests__
```

## 8. Evidence
- diff по 3-4 файлам, вывод vitest.

## 9. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
