
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_ONBOARDING_FLOW
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/onboarding/onboarding-flow.tsx
// owns:
//   - components/onboarding/onboarding-flow.tsx
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

"use client"

import { useReducer, useState } from "react"

import { StepWelcome } from "./step-welcome"
import { StepBirth } from "./step-birth"
import { StepPlace } from "./step-place"
import { StepBirthday } from "./step-birthday"
import { StepGender } from "./step-gender"
import { StepDone } from "./step-done"
import { saveProfile, type Profile } from "@/lib/profile"
import { updateProfile } from "@/lib/api/profile"
import {
  onboardingReducer,
  initialOnboardingState,
  selectEffectiveCurrentCity,
  selectEffectiveBirthdayCity,
} from "@/lib/reducers/onboarding-reducer"
import { logEvent } from "@/lib/log"

type Props = {
  onComplete: () => void
}

/**
 * Онбординг-флоу теперь использует чистый reducer.
 *
 * Компонент стал тонкой оболочкой:
 *  - reducer содержит всю бизнес-логику шагов (тестируется без jsdom);
 *  - компонент отвечает только за рендер и прокидывание событий.
 */
export function OnboardingFlow({ onComplete }: Props) {
  const [state, dispatch] = useReducer(onboardingReducer, initialOnboardingState)
  const [isSaving, setIsSaving] = useState(false)

  const back = () => {
    dispatch({ type: "back" })
  }
  const next = () => {
    dispatch({ type: "next" })
  }

  /**
   * Финиш онбординга: собираем Profile из state, сохраняем
   * в localStorage и отправляем на backend.
   */
  const finish = async () => {
    if (isSaving) return

    if (!state.gender) {
      dispatch({ type: "go_to_step", value: "gender" })
      return
    }
    const gender: "male" | "female" = state.gender

    const birthPlaceCity = state.birthPlace
    const effectiveCurrentCity = selectEffectiveCurrentCity(state)
    const effectiveBirthdayCity = selectEffectiveBirthdayCity(state)

    const birthPlaceStr = birthPlaceCity
      ? `${birthPlaceCity.name}, ${birthPlaceCity.country}`
      : ''
    const currentCityStr = effectiveCurrentCity
      ? `${effectiveCurrentCity.name}, ${effectiveCurrentCity.country}`
      : ''
    const birthdayCityStr = effectiveBirthdayCity
      ? `${effectiveBirthdayCity.name}, ${effectiveBirthdayCity.country}`
      : ''

    const profile: Profile = {
      birthDate: state.birthDate,
      birthTime: state.birthTime,
      birthPlace: birthPlaceStr,
      currentCity: currentCityStr,
      sameAsBirth: state.sameAsBirth,
      birthdayCity: birthdayCityStr,
      birthdaySameAsCurrent: state.birthdaySameAsCurrent,
      gender,
    }

    // Save to localStorage first (for immediate access)
    saveProfile(profile)

    // Send to backend
    setIsSaving(true)
    try {
      // Convert profile to API format
      const birthday = `${profile.birthDate.year}-${profile.birthDate.month.padStart(2, '0')}-${profile.birthDate.day.padStart(2, '0')}`
      const birthTime = profile.birthTime.unknown
        ? undefined
        : `${profile.birthTime.hours.padStart(2, '0')}:${profile.birthTime.minutes.padStart(2, '0')}`

      const currentLocation = effectiveCurrentCity
        ? {
            city: `${effectiveCurrentCity.name}, ${effectiveCurrentCity.country}`,
            lat: effectiveCurrentCity.lat,
            lon: effectiveCurrentCity.lon,
            tz: effectiveCurrentCity.timezone,
          }
        : undefined

      const birthdayLocation = effectiveBirthdayCity
        ? {
            city: `${effectiveBirthdayCity.name}, ${effectiveBirthdayCity.country}`,
            lat: effectiveBirthdayCity.lat,
            lon: effectiveBirthdayCity.lon,
            tz: effectiveBirthdayCity.timezone,
          }
        : undefined

      await updateProfile({
        gender: profile.gender,
        birth: {
          birthday,
          birthTime,
          birthCity: birthPlaceStr,
          birthLat: birthPlaceCity?.lat ?? undefined,
          birthLon: birthPlaceCity?.lon ?? undefined,
          birthTz: birthPlaceCity?.timezone ?? undefined,
        },
        currentLocation: currentLocation ?? undefined,
        birthdayLocation: birthdayLocation ?? undefined,
      })

      logEvent("profile.updated", {}, { msg: "[Onboarding] Profile saved to backend", slice: "W-ONBOARDING", module: "M-ONBOARDING-FLOW", block: "SAVE_PROFILE" })
      onComplete()
    } catch (error) {
      logEvent("profile.update_failed", { error: String(error) }, { msg: "[Onboarding] Failed to save profile to backend", level: "error", slice: "W-ONBOARDING", module: "M-ONBOARDING-FLOW", block: "SAVE_PROFILE" })
      // Still complete onboarding even if backend fails
      // User can retry later from profile page
      onComplete()
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="h-[var(--app-height)] bg-background overflow-hidden">
      <div className="mx-auto flex h-[var(--app-height)] max-w-md flex-col border-x border-border/50 bg-background">
        {state.step === "welcome" ? (
          <StepWelcome onNext={next} onSkip={onComplete} />
        ) : state.step === "birth" ? (
          <StepBirth
            date={state.birthDate}
            time={state.birthTime}
            onChangeDate={(value) => dispatch({ type: "set_birth_date", value })}
            onChangeTime={(value) => dispatch({ type: "set_birth_time", value })}
            onBack={back}
            onNext={next}
          />
        ) : state.step === "place" ? (
          <StepPlace
            birthPlace={state.birthPlace}
            currentCity={state.currentCity}
            sameAsBirth={state.sameAsBirth}
            onChangeBirthPlace={(value) =>
              dispatch({ type: "set_birth_place", value })
            }
            onChangeCurrentCity={(value) =>
              dispatch({ type: "set_current_city", value })
            }
            onChangeSameAsBirth={(value) =>
              dispatch({ type: "set_same_as_birth", value })
            }
            onBack={back}
            onNext={next}
          />
        ) : state.step === "birthday" ? (
          <StepBirthday
            currentCity={selectEffectiveCurrentCity(state)}
            birthdayCity={state.birthdayCity}
            sameAsCurrent={state.birthdaySameAsCurrent}
            onChangeBirthdayCity={(value) =>
              dispatch({ type: "set_birthday_city", value })
            }
            onChangeSameAsCurrent={(value) =>
              dispatch({ type: "set_birthday_same_as_current", value })
            }
            onBack={back}
            onNext={next}
          />
        ) : state.step === "gender" ? (
          <StepGender
            gender={state.gender}
            onSelect={(value) => {
              dispatch({ type: "set_gender", value })
              next()
            }}
            onBack={back}
          />
        ) : (
          <StepDone onFinish={finish} />
        )}
      </div>
    </main>
  )
}
