/**
 * API-фасад для подписки/доступа.
 *
 * Компоненты и хуки ходят сюда, никогда напрямую в моки/fixtures.
 * Переключение между fixtures и реальным API — через ENV:
 *   NEXT_PUBLIC_USE_FIXTURES=true → используем fixtures
 *   production → используем реальный API
 *
 * Когда появится биллинг, реализуем fetchAccess():
 *
 *   async function fetchAccess(): Promise<AccessInfo> {
 *     const res = await fetch(`${API_BASE_URL}/access`, { ... })
 *     if (!res.ok) throw new Error(...)
 *     return validateAccessInfo(await res.json())
 *   }
 */

import {
  type AccessInfo,
  type AccessState,
  validateAccessInfo,
} from "@/lib/contracts/access"
import { USE_FIXTURES } from "./config"

export type { AccessInfo, AccessState }

// ---------------------------------------------------------------------------
// Production implementation (stub — будет заменён на реальный fetch)
// ---------------------------------------------------------------------------

async function fetchAccess(_state: AccessState): Promise<AccessInfo> {
  // TODO: Реализовать когда появится backend
  // const res = await fetch(`${API_BASE_URL}/access`)
  // if (!res.ok) throw new Error(`Access API error: ${res.status}`)
  // return validateAccessInfo(await res.json())

  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getAccess(state: AccessState): AccessInfo {
  if (USE_FIXTURES) {
    // Dynamic import для tree-shaking в production
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getAccessFixture } = require("./access.fixtures") as typeof import("./access.fixtures")
    return getAccessFixture(state)
  }

  // В production — синхронный вызов невозможен без backend
  // Для демо возвращаем дефолтное состояние
  // TODO: переделать на async когда будет backend
  return validateAccessInfo({
    state: state,
    trialDaysLeft: state === "trial" ? 3 : null,
    expiresAt: state === "expired" ? new Date(Date.now() - 86400000).toISOString() : null,
    paywallReason: state === "none" ? "no_subscription" : null,
  })
}

export async function getAccessAsync(state: AccessState): Promise<AccessInfo> {
  if (USE_FIXTURES) {
    const { getAccessFixture } = await import("./access.fixtures")
    return getAccessFixture(state)
  }

  return fetchAccess(state)
}
