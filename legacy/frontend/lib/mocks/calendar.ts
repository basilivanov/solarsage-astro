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
