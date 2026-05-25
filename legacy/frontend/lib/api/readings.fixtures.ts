/**
 * Fixture-реализация для readings API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import type { ReadingsCatalog } from "@/lib/readings"
import { buildMockReadings } from "@/lib/mocks/readings"

export function listReadingsFixture(): ReadingsCatalog {
  return buildMockReadings()
}
