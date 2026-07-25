// ############################################################################
// AI_HEADER: MODULE_LIB_PROFILE
// ROLE: Profile UI model, backend mapping, formatting, and API-sourced cache
// DEPENDENCIES: packages/contracts, lib/storage-keys, lib/contracts/profile
// GRACE_ANCHORS: [PROFILE_CONSTANTS, PROFILE_MAPPERS, PROFILE_FORMATTERS, PROFILE_STORAGE]
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################
"use client"

// START_MODULE_CONTRACT: M-LIB-PROFILE
// purpose: Profile UI model, API format mapping, date/time formatting, and localStorage caching.
// owns:
//   - lib/profile.ts
// inputs: ProfileRead, ProfileWrite, Profile, BirthDateParts, BirthTimeParts
// outputs: Profile mapping functions, formatters, and storage helpers
// dependencies: packages/contracts, lib/storage-keys, lib/contracts/profile
// side_effects: reads/writes localStorage for profile cache
// emitted_logs: none
// failure_policy: falls back to EMPTY_PROFILE on parse/storage errors
// END_MODULE_CONTRACT: M-LIB-PROFILE

// START_MODULE_MAP: M-LIB-PROFILE
// public_entrypoints:
//   - EMPTY_PROFILE
//   - DEFAULT_PROFILE
//   - apiProfileToProfile
//   - profileToApiWrite
//   - formatBirthDate
//   - formatBirthTime
//   - isValidBirthDate
//   - isValidBirthTime
//   - loadProfile
//   - saveProfile
// semantic_blocks:
//   - PROFILE_CONSTANTS: empty and default profile shapes
//   - PROFILE_MAPPERS: apiProfileToProfile and profileToApiWrite
//   - PROFILE_FORMATTERS: formatBirthDate, formatBirthTime, and validators
//   - PROFILE_STORAGE: loadProfile and saveProfile localStorage helpers
// owned_tests:
//   - __tests__/lib/profile.test.ts
// END_MODULE_MAP: M-LIB-PROFILE

import type { ProfileRead, ProfileWrite } from "@/packages/contracts"
import { STORAGE_KEYS } from "@/lib/storage-keys"
import {
  type BirthDateParts,
  type BirthTimeParts,
  type Profile,
  type ProfileLocation,
  safeValidateProfile,
} from "@/lib/contracts/profile"

export type { BirthDateParts, BirthTimeParts, Profile, ProfileLocation }

// START_BLOCK: PROFILE_CONSTANTS
export const EMPTY_PROFILE: Profile = {
  firstName: "",
  birthDate: { day: "", month: "", year: "" },
  birthTime: { hours: "", minutes: "", unknown: true },
  birthPlace: "",
  currentCity: "",
  birthdayCity: "",
  birthLocation: null,
  currentLocation: null,
  birthdayLocation: null,
  gender: null,
  isOnboarded: false,
  sameAsBirth: false,
  birthdaySameAsCurrent: false,
}

// Retained for utility tests and callers that explicitly need sample data.
// Product profile state initializes from EMPTY_PROFILE or an API-sourced cache.
export const DEFAULT_PROFILE: Profile = {
  firstName: "",
  birthDate: { day: "14", month: "07", year: "1995" },
  birthTime: { hours: "08", minutes: "42", unknown: false },
  birthPlace: "Киев, Украина",
  currentCity: "Лиссабон, Португалия",
  birthdayCity: "Лиссабон, Португалия",
  birthLocation: null,
  currentLocation: null,
  birthdayLocation: null,
  gender: "female",
  isOnboarded: true,
  sameAsBirth: false,
  birthdaySameAsCurrent: true,
}
// END_BLOCK: PROFILE_CONSTANTS

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

type ApiLocation = NonNullable<ProfileRead["currentLocation"]>

function toLocation(
  city: string | null | undefined,
  lat: number | null | undefined,
  lon: number | null | undefined,
  timezone: string | null | undefined,
): ProfileLocation | null {
  if (!city && lat == null && lon == null && !timezone) return null
  return {
    city: city ?? "",
    lat: lat ?? null,
    lon: lon ?? null,
    timezone: timezone ?? null,
  }
}

function fromApiLocation(location: ApiLocation | null | undefined): ProfileLocation | null {
  if (!location) return null
  return toLocation(location.city, location.lat, location.lon, location.tz)
}

function toApiLocation(location: ProfileLocation | null): ApiLocation | null {
  if (!location) return null
  return {
    city: location.city || null,
    lat: location.lat,
    lon: location.lon,
    tz: location.timezone,
  }
}

function parseBirthDate(value: string | null | undefined): BirthDateParts {
  if (!value) return EMPTY_PROFILE.birthDate
  const [year = "", month = "", day = ""] = value.split("-")
  return { day, month, year }
}

function parseBirthTime(value: string | null | undefined): BirthTimeParts {
  if (!value) return EMPTY_PROFILE.birthTime
  const [hours = "", minutes = ""] = value.split(":")
  return { hours, minutes, unknown: false }
}

function serializeBirthDate(value: BirthDateParts): string | null {
  if (!isValidBirthDate(value)) return null
  return `${value.year}-${value.month.padStart(2, "0")}-${value.day.padStart(2, "0")}`
}

function serializeBirthTime(value: BirthTimeParts): string | null {
  if (value.unknown || !isValidBirthTime(value)) return null
  return `${value.hours.padStart(2, "0")}:${value.minutes.padStart(2, "0")}:00`
}

// START_BLOCK: PROFILE_MAPPERS
export function apiProfileToProfile(value: ProfileRead): Profile {
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.apiProfileToProfile
  // purpose: Convert backend ProfileRead object into frontend Profile representation.
  // inputs: value (ProfileRead)
  // returns: Profile
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.apiProfileToProfile
  const birthLocation = toLocation(
    value.birth.birthCity,
    value.birth.birthLat,
    value.birth.birthLon,
    value.birth.birthTz,
  )
  const currentLocation = fromApiLocation(value.currentLocation)
  const birthdayLocation = fromApiLocation(value.birthdayLocation)
  const birthPlace = birthLocation?.city ?? ""
  const currentCity = currentLocation?.city ?? ""
  const birthdayCity = birthdayLocation?.city ?? ""

  return {
    firstName: value.firstName ?? "",
    birthDate: parseBirthDate(value.birth.birthday),
    birthTime: parseBirthTime(value.birth.birthTime),
    birthPlace,
    currentCity,
    birthdayCity,
    birthLocation,
    currentLocation,
    birthdayLocation,
    gender: value.gender ?? null,
    isOnboarded: value.isOnboarded,
    sameAsBirth: Boolean(birthPlace && currentCity && birthPlace === currentCity),
    birthdaySameAsCurrent: Boolean(
      currentCity && birthdayCity && currentCity === birthdayCity,
    ),
  }
}

export function profileToApiWrite(profile: Profile): ProfileWrite {
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.profileToApiWrite
  // purpose: Convert frontend Profile object into backend ProfileWrite payload.
  // inputs: profile (Profile)
  // returns: ProfileWrite
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.profileToApiWrite
  const birthLocation = profile.birthLocation
    ? { ...profile.birthLocation, city: profile.birthPlace }
    : profile.birthPlace
      ? { city: profile.birthPlace, lat: null, lon: null, timezone: null }
      : null
  const currentLocation = profile.currentLocation
    ? { ...profile.currentLocation, city: profile.currentCity }
    : profile.currentCity
      ? { city: profile.currentCity, lat: null, lon: null, timezone: null }
      : null
  const birthdayLocation = profile.birthdayLocation
    ? { ...profile.birthdayLocation, city: profile.birthdayCity }
    : profile.birthdayCity
      ? { city: profile.birthdayCity, lat: null, lon: null, timezone: null }
      : null

  return {
    firstName: profile.firstName || null,
    gender: profile.gender,
    birth: {
      birthday: serializeBirthDate(profile.birthDate),
      birthTime: serializeBirthTime(profile.birthTime),
      birthCity: birthLocation?.city || null,
      birthLat: birthLocation?.lat ?? null,
      birthLon: birthLocation?.lon ?? null,
      birthTz: birthLocation?.timezone ?? null,
    },
    currentLocation: toApiLocation(currentLocation),
    birthdayLocation: toApiLocation(birthdayLocation),
  }
}
// END_BLOCK: PROFILE_MAPPERS

// START_BLOCK: PROFILE_FORMATTERS
export function formatBirthDate(d: BirthDateParts): string {
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.formatBirthDate
  // purpose: Format BirthDateParts into human-readable Russian date string.
  // inputs: d (BirthDateParts)
  // returns: string
  // side_effects: none
  // error_behavior: returns "Не указано" on invalid date parts
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.formatBirthDate
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
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.formatBirthTime
  // purpose: Format BirthTimeParts into human-readable HH:MM string or "Не знаю".
  // inputs: t (BirthTimeParts)
  // returns: string
  // side_effects: none
  // error_behavior: returns "Не знаю" if unknown, "Не указано" if malformed
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.formatBirthTime
  if (t.unknown) return "Не знаю"
  const h = t.hours.padStart(2, "0")
  const m = t.minutes.padStart(2, "0")
  if (!/^\d{2}$/.test(h) || !/^\d{2}$/.test(m)) return "Не указано"
  return `${h}:${m}`
}

export function isValidBirthDate(d: BirthDateParts): boolean {
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.isValidBirthDate
  // purpose: Validate BirthDateParts values against calendar boundaries.
  // inputs: d (BirthDateParts)
  // returns: boolean
  // side_effects: none
  // error_behavior: returns false on invalid input
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.isValidBirthDate
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
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.isValidBirthTime
  // purpose: Validate BirthTimeParts values against time boundaries or unknown flag.
  // inputs: t (BirthTimeParts)
  // returns: boolean
  // side_effects: none
  // error_behavior: returns false on invalid input
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.isValidBirthTime
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
// END_BLOCK: PROFILE_FORMATTERS

// START_BLOCK: PROFILE_STORAGE
export function loadProfile(): Profile {
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.loadProfile
  // purpose: Load cached Profile from localStorage with validation.
  // inputs: none
  // returns: Profile (or EMPTY_PROFILE on missing/invalid cache)
  // side_effects: reads localStorage
  // error_behavior: returns EMPTY_PROFILE on any storage/validation error
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.loadProfile
  if (typeof window === "undefined") return EMPTY_PROFILE
  try {
    const raw = window.localStorage.getItem(STORAGE_KEYS.profile)
    if (!raw) return EMPTY_PROFILE
    const parsed = JSON.parse(raw)
    if (parsed?.source !== "api") return EMPTY_PROFILE
    const result = safeValidateProfile(parsed.profile)
    return result.success ? result.data : EMPTY_PROFILE
  } catch {
    return EMPTY_PROFILE
  }
}

export function saveProfile(profile: Profile): void {
  // START_FUNCTION_CONTRACT: F-M-LIB-PROFILE.saveProfile
  // purpose: Persist Profile to localStorage cache.
  // inputs: profile (Profile)
  // returns: void
  // side_effects: writes localStorage
  // error_behavior: catches storage exceptions silently
  // END_FUNCTION_CONTRACT: F-M-LIB-PROFILE.saveProfile
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(
      STORAGE_KEYS.profile,
      JSON.stringify({ source: "api", profile }),
    )
  } catch {
    // Cache failures must not block the API-backed profile flow.
  }
}
// END_BLOCK: PROFILE_STORAGE
