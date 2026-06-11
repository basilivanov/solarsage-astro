
// ############################################################################
// AI_HEADER: MODULE_MOCKS_ACCESS
// ROLE: Lib — access.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Library: access
// owns:
//   - lib/mocks/access.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Мок построения окна доступа.
 *
 * Используется ИСКЛЮЧИТЕЛЬНО из `lib/api/access.ts`. Когда подключим
 * биллинг, бэкенд будет отдавать готовый `AccessInfo` целиком — этот
 * файл просто удалится.
 */

import type { AccessInfo, AccessState } from "@/lib/contracts/access"
import { TODAY, addDays, stripTime } from "@/lib/today"

/**
 * Строит синтетическое окно доступа относительно TODAY.
 * - trial: 14 дней начиная с сегодня (today..today+13)
 * - subscription: 14 дней назад и 30 вперёд (демо-окно)
 * - expired: окно закончилось вчера (14 прошлых дней)
 * - none: окна нет
 */
export function buildMockAccess(state: AccessState): AccessInfo {
  switch (state) {
    case "trial": {
      const start = stripTime(TODAY)
      const end = addDays(start, 13)
      return {
        state,
        hasAccess: true,
        accessStart: start,
        accessEnd: end,
        daysLeft: 14,
      }
    }
    case "subscription": {
      const start = addDays(stripTime(TODAY), -14)
      const end = addDays(stripTime(TODAY), 30)
      return {
        state,
        hasAccess: true,
        accessStart: start,
        accessEnd: end,
        daysLeft: 30,
      }
    }
    case "expired": {
      // У пользователя был 14-дневный триал, он закончился вчера
      const end = addDays(stripTime(TODAY), -1)
      const start = addDays(end, -13)
      return {
        state,
        hasAccess: false,
        accessStart: start,
        accessEnd: end,
        daysLeft: 0,
      }
    }
    case "none":
    default:
      return {
        state: "none",
        hasAccess: false,
        accessStart: null,
        accessEnd: null,
        daysLeft: 0,
      }
  }
}
