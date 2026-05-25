/**
 * Fixture-реализация для profile-meta API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import type { ProfileMeta } from "@/lib/profile-meta"
import { buildMockProfileMeta } from "@/lib/mocks/profile-meta"

export function getProfileMetaFixture(): ProfileMeta {
  return buildMockProfileMeta()
}
