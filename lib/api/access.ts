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
