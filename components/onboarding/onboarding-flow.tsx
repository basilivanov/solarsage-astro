
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_ONBOARDING_FLOW
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT: M-ONBOARDING-ONBOARDING-FLOW
// purpose: Onboarding flow component managing step transitions, profile prefill, exact-time validation, and profile save.
// owns:
//   - components/onboarding/onboarding-flow.tsx
// inputs: onComplete, initialState, requireExactBirthTime
// outputs: OnboardingFlow React component
// dependencies: onboardingReducer, updateProfile, saveProfile, logEvent
// side_effects: calls updateProfile API, saves profile cache to localStorage, emits log events
// emitted_logs: profile.updated, profile.update_failed
// failure_policy: displays error message on save failure and enables retry
// END_MODULE_CONTRACT: M-ONBOARDING-ONBOARDING-FLOW

// START_MODULE_MAP: M-ONBOARDING-ONBOARDING-FLOW
// public_entrypoints:
//   - OnboardingFlow
// semantic_blocks:
//   - ONBOARDING_FLOW_COMPONENT: main onboarding step flow component
// owned_tests:
//   - __tests__/components/OnboardingFlow.test.tsx
// END_MODULE_MAP: M-ONBOARDING-ONBOARDING-FLOW
"use client"

import { useReducer, useState } from "react"

import { StepWelcome } from "./step-welcome"
import { StepBirth } from "./step-birth"
import { StepPlace } from "./step-place"
import { StepBirthday } from "./step-birthday"
import { StepGender } from "./step-gender"
import { StepDone } from "./step-done"
import { apiProfileToProfile, saveProfile } from "@/lib/profile"
import { updateProfile } from "@/lib/api/profile"
import {
  onboardingReducer,
  initialOnboardingState,
  selectEffectiveCurrentCity,
  selectEffectiveBirthdayCity,
} from "@/lib/reducers/onboarding-reducer"
import { logEvent } from "@/lib/log"

import type { OnboardingState } from "@/lib/reducers/onboarding-reducer"

type Props = {
  onComplete: () => void
  initialState?: OnboardingState
  requireExactBirthTime?: boolean
}

/**
 * Онбординг-флоу теперь использует чистый reducer.
 *
 * Компонент стал тонкой оболочкой:
 *  - reducer содержит всю бизнес-логику шагов (тестируется без jsdom);
 *  - компонент отвечает только за рендер и прокидывание событий.
 */
// START_BLOCK: ONBOARDING_FLOW_COMPONENT
export function OnboardingFlow({
  onComplete,
  initialState,
  requireExactBirthTime = false,
}: Props) {
  const [state, dispatch] = useReducer(
    onboardingReducer,
    initialState || initialOnboardingState
  )
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

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

    if (requireExactBirthTime) {
      if (
        state.birthTime.unknown ||
        !state.birthTime.hours ||
        !state.birthTime.minutes
      ) {
        dispatch({ type: "go_to_step", value: "birth" })
        return
      }
    }

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

    // Send to backend
    setIsSaving(true)
    setSaveError(null)
    try {
      // Convert profile to API format
      const birthday = `${state.birthDate.year}-${state.birthDate.month.padStart(2, '0')}-${state.birthDate.day.padStart(2, '0')}`
      const birthTime = state.birthTime.unknown
        ? undefined
        : `${state.birthTime.hours.padStart(2, '0')}:${state.birthTime.minutes.padStart(2, '0')}`

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

      const saved = await updateProfile({
        gender,
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
      saveProfile(apiProfileToProfile(saved))

      logEvent("profile.updated", {}, { msg: "[Onboarding] Profile saved to backend", slice: "W-ONBOARDING", module: "M-ONBOARDING-FLOW", block: "SAVE_PROFILE" })
      onComplete()
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось сохранить профиль"
      setSaveError(message)
      logEvent("profile.update_failed", { error: String(error) }, { msg: "[Onboarding] Failed to save profile to backend", level: "error", slice: "W-ONBOARDING", module: "M-ONBOARDING-FLOW", block: "SAVE_PROFILE" })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="h-[var(--app-height)] bg-background overflow-hidden">
      <div className="mx-auto flex h-[var(--app-height)] max-w-md flex-col border-x border-border/50 bg-background">
        {state.step === "welcome" ? (
          <StepWelcome onNext={next} />
        ) : state.step === "birth" ? (
          <StepBirth
            date={state.birthDate}
            time={state.birthTime}
            onChangeDate={(value) => dispatch({ type: "set_birth_date", value })}
            onChangeTime={(value) => dispatch({ type: "set_birth_time", value })}
            onBack={back}
            onNext={next}
            requireExactBirthTime={requireExactBirthTime}
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
          <StepDone
            onFinish={finish}
            saving={isSaving}
            error={saveError}
          />
        )}
      </div>
    </main>
  )
}
// END_BLOCK: ONBOARDING_FLOW_COMPONENT
