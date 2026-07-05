// ############################################################################
// AI_HEADER: MODULE_LIB_PROFILE
// ROLE: Profile UI model, backend mapping, formatting, and API-sourced cache
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
"use client"

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

export function apiProfileToProfile(value: ProfileRead): Profile {
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
