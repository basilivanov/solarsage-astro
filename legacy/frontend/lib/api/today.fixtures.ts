/**
 * Fixture-реализация для today API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import {
  type TodayPayload,
  validateTodayPayload,
} from "@/lib/contracts/today"
import { buildMockTodayPayload } from "@/lib/mocks/today"

export function getTodayPayloadFixture(date: Date): TodayPayload {
  const raw = buildMockTodayPayload(date)
  return validateTodayPayload(raw)
}
