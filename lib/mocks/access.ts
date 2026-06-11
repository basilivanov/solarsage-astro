
// ############################################################################
// AI_HEADER: MODULE_MOCKS_ACCESS
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/mocks/access.ts
// owns:
//   - lib/mocks/access.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

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
