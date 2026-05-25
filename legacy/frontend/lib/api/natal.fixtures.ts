/**
 * Fixture-реализация для natal API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import {
  type NatalReport,
  validateNatalReport,
} from "@/lib/contracts/natal"
import { MOCK_NATAL_REPORT } from "@/lib/mocks/natal"

export function getNatalReportFixture(): NatalReport {
  const raw = MOCK_NATAL_REPORT
  return validateNatalReport(raw)
}

export function getNatalSectionFixture(id: string) {
  const report = getNatalReportFixture()
  const idx = report.sections.findIndex((s) => s.id === id)
  if (idx === -1) return null
  return {
    report,
    section: report.sections[idx],
    prev: idx > 0 ? report.sections[idx - 1] : null,
    next: idx < report.sections.length - 1 ? report.sections[idx + 1] : null,
    index: idx,
    total: report.sections.length,
  }
}
