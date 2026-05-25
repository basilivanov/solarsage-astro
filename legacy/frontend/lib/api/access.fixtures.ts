/**
 * Fixture-реализация для access API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import {
  type AccessInfo,
  type AccessState,
  validateAccessInfo,
} from "@/lib/contracts/access"
import { buildMockAccess } from "@/lib/mocks/access"

export function getAccessFixture(state: AccessState): AccessInfo {
  const raw = buildMockAccess(state)
  return validateAccessInfo(raw)
}
