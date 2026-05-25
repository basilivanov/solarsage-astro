/**
 * Fixture-реализация для cities API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import { type City, validateCities } from "@/lib/contracts/city"
import { getMockPopularCities, searchMockCities } from "@/lib/mocks/cities"

export function searchCitiesFixture(query: string, limit?: number): City[] {
  const raw = searchMockCities(query, limit)
  return validateCities(raw)
}

export function getPopularCitiesFixture(): string[] {
  return getMockPopularCities()
}
