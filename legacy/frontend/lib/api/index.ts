/**
 * API Layer — Единая точка входа для всех API-вызовов.
 *
 * Архитектура:
 *
 * 1. Контракты (lib/contracts/*) — zod-схемы, определяющие формат данных.
 *    Единственный источник правды для типов между frontend и backend.
 *
 * 2. API-фасады (lib/api/*.ts) — публичные функции для компонентов.
 *    Компоненты импортируют только отсюда, никогда из fixtures или mocks.
 *
 * 3. Fixtures (lib/api/*.fixtures.ts) — мок-реализации для dev/e2e.
 *    Подключаются через ENV: NEXT_PUBLIC_USE_FIXTURES=true
 *    В production недостижимы (tree-shake).
 *
 * 4. Mocks (lib/mocks/*) — генераторы тестовых данных.
 *    Используются только из fixtures, никогда напрямую из компонентов.
 *
 * Переключение режимов:
 *   - development: USE_FIXTURES=true (по умолчанию)
 *   - production: USE_FIXTURES=false, требуется реальный backend
 *
 * Пример миграции на реальный API:
 *
 *   // lib/api/access.ts
 *   export async function getAccessAsync(): Promise<AccessInfo> {
 *     if (USE_FIXTURES) {
 *       const { getAccessFixture } = await import("./access.fixtures")
 *       return getAccessFixture(state)
 *     }
 *     const res = await fetch(`${API_BASE_URL}/access`)
 *     if (!res.ok) throw new Error(`API error: ${res.status}`)
 *     return validateAccessInfo(await res.json())
 *   }
 */

// Config
export { USE_FIXTURES, API_BASE_URL } from "./config"

// Access
export { getAccess, getAccessAsync, type AccessInfo, type AccessState } from "./access"

// Calendar
export {
  getDayStatus,
  getMonthStatuses,
  getDayStatusAsync,
  getMonthStatusesAsync,
  type DayStatus,
  type DayStatusMap,
} from "./calendar"

// Chat
export { sendMessage, type ChatContext, type ChatMessage } from "./chat"

// Cities
export {
  searchCities,
  getPopularCities,
  searchCitiesAsync,
  getPopularCitiesAsync,
  type City,
} from "./cities"

// Natal
export {
  getNatalReport,
  getNatalSection,
  getNatalReportAsync,
  getNatalSectionAsync,
  type NatalReport,
  type ReportSection,
} from "./natal"

// Profile Meta
export { getProfileMeta, getProfileMetaAsync } from "./profile-meta"

// Readings
export { listReadings, listReadingsAsync } from "./readings"

// Today
export { getTodayPayload, getTodayPayloadAsync, type TodayPayload } from "./today"
