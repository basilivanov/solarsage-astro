"use client"

import { useReducer, useState } from "react"

import { StepWelcome } from "./step-welcome"
import { StepBirth } from "./step-birth"
import { StepPlace } from "./step-place"
import { StepBirthday } from "./step-birthday"
import { StepDone } from "./step-done"
import { saveProfile, type Profile } from "@/lib/profile"
import { updateProfile } from "@/lib/api/profile"
import {
  onboardingReducer,
  initialOnboardingState,
  selectEffectiveCurrentCity,
  selectEffectiveBirthdayCity,
} from "@/lib/reducers/onboarding-reducer"

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
    console.log('[Onboarding] Back clicked, current step:', state.step)
    dispatch({ type: "back" })
  }
  const next = () => {
    console.log('[Onboarding] Next clicked, current step:', state.step)
    dispatch({ type: "next" })
  }

  /**
   * Финиш онбординга: собираем Profile из state, сохраняем
   * в localStorage и отправляем на backend.
   */
  const finish = async () => {
    if (isSaving) return

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

      await updateProfile({
        birth: {
          birthday,
          birthTime,
          birthCity: birthPlaceStr,
          birthLat: birthPlaceCity?.lat ?? undefined,
          birthLon: birthPlaceCity?.lon ?? undefined,
          birthTz: birthPlaceCity?.timezone ?? undefined,
        },
      })

      console.log('[Onboarding] Profile saved to backend')
      onComplete()
    } catch (error) {
      console.error('[Onboarding] Failed to save profile to backend:', error)
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
        ) : (
          <StepDone onFinish={finish} />
        )}
      </div>
    </main>
  )
}
