/**
 * Fixture-реализация для calendar API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import { dateKey, monthMatrix } from "@/lib/calendar"
import {
  type DayStatus,
  type DayStatusMap,
  validateDayStatus,
  validateDayStatusMap,
} from "@/lib/contracts/calendar"
import { buildMockDayStatus } from "@/lib/mocks/calendar"

export function getDayStatusFixture(date: Date): DayStatus {
  const raw = buildMockDayStatus(date)
  return validateDayStatus(raw)
}

export function getMonthStatusesFixture(
  year: number,
  month: number,
): DayStatusMap {
  const out: Record<string, DayStatus> = {}
  for (const { date } of monthMatrix(year, month)) {
    out[dateKey(date)] = buildMockDayStatus(date)
  }
  return validateDayStatusMap(out)
}
