
// ############################################################################
// AI_HEADER: MODULE_LIB_STORAGE_KEYS
// ROLE: UI — storage-keys
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI storage-keys — component
// owns:
//   - lib/storage-keys.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Все ключи `localStorage` живут здесь. Один namespace, одно место.
 *
 * Зачем:
 *  - проще аудитить, что приложение пишет в браузер;
 *  - проще делать «полный сброс» (см. `clearAllStorage`);
 *  - переименование ключа не разъезжается по всему дереву.
 *
 * Соглашение: префикс `lumen:` + короткое имя домена.
 * При несовместимом изменении формата — добавляем суффикс версии,
 * например `lumen:profile` → `lumen:profile.v2`.
 */

export const STORAGE_KEYS = {
  /** Анкета пользователя (дата/время/места рождения, чекбоксы). */
  profile: "lumen:profile",
  /** История сообщений чата с агентом. */
  chat: "lumen:chat",
  /** Текущее состояние доступа: trial / subscription / expired / none. */
  accessState: "lumen:access-state",
  /** Флаг «онбординг пройден» — `"1"`, иначе ключа нет. */
  onboarded: "lumen:onboarded",
} as const

export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS]

/**
 * Полный сброс приложения. Удобно дёргать из dev-меню профиля,
 * не вспоминая, какие именно ключи существуют.
 */
export function clearAllStorage(): void {
  if (typeof window === "undefined") return
  try {
    for (const key of Object.values(STORAGE_KEYS)) {
      window.localStorage.removeItem(key)
    }
  } catch {
    /* quota / private mode — игнорируем */
  }
}
