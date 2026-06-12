
// ############################################################################
// AI_HEADER: MODULE_REDUCERS_ONBOARDING_REDUCER
// ROLE: UI — onboarding-reducer
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI onboarding-reducer — component
// owns:
//   - lib/reducers/onboarding-reducer.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Чистый reducer для онбординга — вся бизнес-логика шагов без side-effects.
 *
 * Преимущества:
 *  - тестируется без jsdom, RTL;
 *  - валидаторы шагов отделены от UI;
 *  - компонент тестируется только тем, что правильно прокидывает ввод в reducer.
 */

import type { BirthDateParts, BirthTimeParts } from "@/lib/contracts/profile"
import type { City } from "@/lib/contracts/city"

// Алиасы для совместимости с reducer API
export type BirthDate = BirthDateParts
export type BirthTime = BirthTimeParts

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export type StepKey = "welcome" | "birth" | "place" | "birthday" | "gender" | "done"

export const STEP_ORDER: readonly StepKey[] = [
  "welcome",
  "birth",
  "place",
  "birthday",
  "gender",
  "done",
] as const

export interface OnboardingState {
  step: StepKey
  birthDate: BirthDate
  birthTime: BirthTime
  birthPlace: City | null
  currentCity: City | null
  sameAsBirth: boolean
  birthdayCity: City | null
  birthdaySameAsCurrent: boolean
  gender: "male" | "female" | null
}

export const initialOnboardingState: OnboardingState = {
  step: "welcome",
  birthDate: { day: "", month: "", year: "" },
  birthTime: { hours: "", minutes: "", unknown: false },
  birthPlace: null,
  currentCity: null,
  sameAsBirth: false,
  birthdayCity: null,
  birthdaySameAsCurrent: true,
  gender: null,
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

export type OnboardingEvent =
  | { type: "next" }
  | { type: "back" }
  | { type: "skip" }
  | { type: "set_birth_date"; value: BirthDate }
  | { type: "set_birth_time"; value: BirthTime }
  | { type: "set_birth_place"; value: City | null }
  | { type: "set_current_city"; value: City | null }
  | { type: "set_same_as_birth"; value: boolean }
  | { type: "set_birthday_city"; value: City | null }
  | { type: "set_birthday_same_as_current"; value: boolean }
  | { type: "set_gender"; value: "male" | "female" | null }
  | { type: "go_to_step"; value: StepKey }
  | { type: "reset" }

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

export function onboardingReducer(
  state: OnboardingState,
  event: OnboardingEvent
): OnboardingState {

  switch (event.type) {
    case "next": {
      const idx = STEP_ORDER.indexOf(state.step)
      const nextIdx = Math.min(idx + 1, STEP_ORDER.length - 1)
      const nextState = { ...state, step: STEP_ORDER[nextIdx] }
      return nextState
    }

    case "back": {
      const idx = STEP_ORDER.indexOf(state.step)
      const prevIdx = Math.max(idx - 1, 0)
      return { ...state, step: STEP_ORDER[prevIdx] }
    }

    case "skip":
      return { ...state, step: "done" }

    case "go_to_step":
      if (STEP_ORDER.includes(event.value)) {
        return { ...state, step: event.value }
      }
      return state

    case "set_birth_date":
      return { ...state, birthDate: event.value }

    case "set_birth_time":
      return { ...state, birthTime: event.value }

    case "set_birth_place":
      return { ...state, birthPlace: event.value }

    case "set_current_city":
      return { ...state, currentCity: event.value }

    case "set_same_as_birth":
      return { ...state, sameAsBirth: event.value }

    case "set_birthday_city":
      return { ...state, birthdayCity: event.value }

    case "set_birthday_same_as_current":
      return { ...state, birthdaySameAsCurrent: event.value }

    case "set_gender":
      return { ...state, gender: event.value }

    case "reset":
      return initialOnboardingState

    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Validators
// ---------------------------------------------------------------------------

export function isValidBirthDate(date: BirthDate): boolean {
  const day = parseInt(date.day, 10)
  const month = parseInt(date.month, 10)
  const year = parseInt(date.year, 10)

  if (isNaN(day) || isNaN(month) || isNaN(year)) return false
  if (day < 1 || day > 31) return false
  if (month < 1 || month > 12) return false
  if (year < 1900 || year > new Date().getFullYear()) return false

  // Проверка реальной даты
  const testDate = new Date(year, month - 1, day)
  return (
    testDate.getDate() === day &&
    testDate.getMonth() === month - 1 &&
    testDate.getFullYear() === year
  )
}

export function isValidBirthTime(time: BirthTime): boolean {
  if (time.unknown) return true

  const hours = parseInt(time.hours, 10)
  const minutes = parseInt(time.minutes, 10)

  if (isNaN(hours) || isNaN(minutes)) return false
  if (hours < 0 || hours > 23) return false
  if (minutes < 0 || minutes > 59) return false

  return true
}

export function isStepValid(state: OnboardingState): boolean {
  switch (state.step) {
    case "welcome":
      return true

    case "birth":
      return isValidBirthDate(state.birthDate) && isValidBirthTime(state.birthTime)

    case "place":
      if (!state.birthPlace) return false
      if (!state.sameAsBirth && !state.currentCity) return false
      return true

    case "birthday":
      if (!state.birthdaySameAsCurrent && !state.birthdayCity) return false
      return true

    case "gender":
      return state.gender !== null

    case "done":
      return true

    default:
      return false
  }
}

// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------

export function selectEffectiveCurrentCity(state: OnboardingState): City | null {
  return state.sameAsBirth ? state.birthPlace : state.currentCity
}

export function selectEffectiveBirthdayCity(state: OnboardingState): City | null {
  if (state.birthdaySameAsCurrent) {
    return selectEffectiveCurrentCity(state)
  }
  return state.birthdayCity
}

export function selectProgress(state: OnboardingState): number {
  const idx = STEP_ORDER.indexOf(state.step)
  return (idx / (STEP_ORDER.length - 1)) * 100
}

export function selectIsFirstStep(state: OnboardingState): boolean {
  return state.step === STEP_ORDER[0]
}

export function selectIsLastStep(state: OnboardingState): boolean {
  return state.step === STEP_ORDER[STEP_ORDER.length - 1]
}
