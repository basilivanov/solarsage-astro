
// ############################################################################
// AI_HEADER: MODULE_LIB_PROFILE
// ROLE: Tests — profile.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for profile.ts behavior
// owns:
//   - lib/profile.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { STORAGE_KEYS } from "@/lib/storage-keys"
import {
  type BirthDateParts,
  type BirthTimeParts,
  type Profile,
  safeValidateProfile,
} from "@/lib/contracts/profile"

// Реэкспорт типов из контрактов
export type { BirthDateParts, BirthTimeParts, Profile }

export const DEFAULT_PROFILE: Profile = {
  birthDate: { day: "14", month: "07", year: "1995" },
  birthTime: { hours: "08", minutes: "42", unknown: false },
  birthPlace: "Киев, Украина",
  currentCity: "Лиссабон, Португалия",
  birthdayCity: "Лиссабон, Португалия",
  gender: "female",
  sameAsBirth: false,
  birthdaySameAsCurrent: true,
}

const MONTHS_GEN = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
]

export function formatBirthDate(d: BirthDateParts): string {
  const day = Number(d.day)
  const month = Number(d.month)
  const year = Number(d.year)
  if (
    Number.isNaN(day) ||
    Number.isNaN(month) ||
    Number.isNaN(year) ||
    month < 1 ||
    month > 12
  ) {
    return "Не указано"
  }
  return `${day} ${MONTHS_GEN[month - 1]} ${year}`
}

export function formatBirthTime(t: BirthTimeParts): string {
  if (t.unknown) return "Не знаю"
  const h = t.hours.padStart(2, "0")
  const m = t.minutes.padStart(2, "0")
  if (!/^\d{2}$/.test(h) || !/^\d{2}$/.test(m)) return "Не указано"
  return `${h}:${m}`
}

export function isValidBirthDate(d: BirthDateParts): boolean {
  const day = Number(d.day)
  const month = Number(d.month)
  const year = Number(d.year)
  return (
    /^\d{1,2}$/.test(d.day) &&
    day >= 1 &&
    day <= 31 &&
    /^\d{1,2}$/.test(d.month) &&
    month >= 1 &&
    month <= 12 &&
    /^\d{4}$/.test(d.year) &&
    year >= 1900 &&
    year <= new Date().getFullYear()
  )
}

export function isValidBirthTime(t: BirthTimeParts): boolean {
  if (t.unknown) return true
  const h = Number(t.hours)
  const m = Number(t.minutes)
  return (
    /^\d{1,2}$/.test(t.hours) &&
    h >= 0 &&
    h <= 23 &&
    /^\d{1,2}$/.test(t.minutes) &&
    m >= 0 &&
    m <= 59
  )
}

export function loadProfile(): Profile {
  if (typeof window === "undefined") return DEFAULT_PROFILE
  try {
    const raw = window.localStorage.getItem(STORAGE_KEYS.profile)
    if (!raw) return DEFAULT_PROFILE
    const parsed = JSON.parse(raw)
    
    // Используем zod-валидацию для безопасной загрузки
    const result = safeValidateProfile({
      ...DEFAULT_PROFILE,
      ...parsed,
      birthDate: { ...DEFAULT_PROFILE.birthDate, ...parsed.birthDate },
      birthTime: { ...DEFAULT_PROFILE.birthTime, ...parsed.birthTime },
    })
    
    if (result.success) {
      return result.data
    }
    
    // При ошибке валидации возвращаем дефолт
    return DEFAULT_PROFILE
  } catch {
    return DEFAULT_PROFILE
  }
}

export function saveProfile(p: Profile) {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(STORAGE_KEYS.profile, JSON.stringify(p))
  } catch {
    /* ignore */
  }
}
