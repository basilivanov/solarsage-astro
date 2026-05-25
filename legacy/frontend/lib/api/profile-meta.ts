/**
 * API-фасад для «меты» профиля.
 *
 * Компоненты ходят сюда, никогда напрямую в fixtures.
 * Переключение между fixtures и реальным API — через ENV.
 */

import type { ProfileMeta } from "@/lib/profile-meta"
import { USE_FIXTURES } from "./config"

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getProfileMeta(): ProfileMeta {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getProfileMetaFixture } = require("./profile-meta.fixtures") as typeof import("./profile-meta.fixtures")
    return getProfileMetaFixture()
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

// ---------------------------------------------------------------------------
// Async version for future backend integration
// ---------------------------------------------------------------------------

export async function getProfileMetaAsync(): Promise<ProfileMeta> {
  if (USE_FIXTURES) {
    const { getProfileMetaFixture } = await import("./profile-meta.fixtures")
    return getProfileMetaFixture()
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}
