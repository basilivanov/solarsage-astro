
// ############################################################################
// AI_HEADER: MODULE_MOCKS_CALENDAR
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/mocks/calendar.ts
// owns:
//   - lib/mocks/calendar.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

// AI_HEADER
// module: M-MOCKS-CALENDAR
// wave: W-2.7
// purpose: Calendar mocks (migrated from legacy)

/**
 * Mock-«тон дня» для календаря.
 *
 * Импортируется ТОЛЬКО из `lib/api/calendar.ts` — компоненты не должны знать
 * об этом файле. Когда появится бэкенд (астрологический расчёт пакетом на
 * месяц), удаляем этот файл и переписываем `lib/api/calendar.ts` на fetch.
 *
 * Сейчас здесь живёт детерминированный плейсхолдер по хешу даты —
 * единственная бизнес-логика, которая раньше сидела прямо в UI.
 */

import type { DayStatus } from "@/lib/contracts/calendar"

export function buildMockDayStatus(d: Date): DayStatus {
  const n = (d.getFullYear() * 372 + (d.getMonth() + 1) * 31 + d.getDate()) % 7
  if (n === 0 || n === 4) return "tense"
  if (n === 2 || n === 6) return "supportive"
  return "even"
}
