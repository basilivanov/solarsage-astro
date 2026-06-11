
// ############################################################################
// AI_HEADER: MODULE_API_ACCESS
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/api/access.ts
// owns:
//   - lib/api/access.ts
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
 * API-фасад для подписки/доступа.
 *
 * Единая точка интеграции для компонентов и хуков.
 * Синхронная версия возвращает дефолтное состояние,
 * async-версия резолвится через fetchAccess (будущий бэкенд-эндпоинт).
 */

import {
  type AccessInfo,
  type AccessState,
  validateAccessInfo,
} from "@/lib/contracts/access"

export type { AccessInfo, AccessState }

function computeAccess(state: AccessState): AccessInfo {
  const now = new Date()
  const hasAccess = state === "trial" || state === "subscription"
  const daysLeft = state === "trial" ? 14 : state === "subscription" ? 30 : 0

  return validateAccessInfo({
    state,
    hasAccess,
    accessStart: hasAccess ? now : null,
    accessEnd: hasAccess ? new Date(now.getTime() + daysLeft * 86400000) : null,
    daysLeft,
  })
}

export function getAccess(state: AccessState): AccessInfo {
  return computeAccess(state)
}

export async function getAccessAsync(state: AccessState): Promise<AccessInfo> {
  return computeAccess(state)
}
