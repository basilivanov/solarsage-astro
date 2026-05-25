/**
 * Mock-данные «меты» профиля.
 *
 * Импортируется ТОЛЬКО из `lib/api/profile-meta.ts` — компоненты не должны
 * знать об этом файле. Когда появится бэкенд, удаляем этот модуль и
 * переписываем `lib/api/profile-meta.ts` на fetch + Zod-валидацию.
 */

import type { ProfileMeta } from "@/lib/profile-meta"

const MOCK: ProfileMeta = {
  horary: {
    left: 2,
    nextInDays: 4,
  },
  referral: {
    count: 0,
    bonusDays: 0,
    rewardDays: 14,
  },
}

export function buildMockProfileMeta(): ProfileMeta {
  // Возвращаем копию, чтобы случайная мутация в UI не утекла обратно в мок.
  return {
    horary: { ...MOCK.horary },
    referral: { ...MOCK.referral },
  }
}
