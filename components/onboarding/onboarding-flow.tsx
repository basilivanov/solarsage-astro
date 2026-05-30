"use client"

import { useReducer } from "react"

import { StepWelcome } from "./step-welcome"
import { StepBirth } from "./step-birth"
import { StepPlace } from "./step-place"
import { StepBirthday } from "./step-birthday"
import { StepDone } from "./step-done"
import { saveProfile, type Profile } from "@/lib/profile"
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

  const back = () => {
    console.log('[Onboarding] Back clicked, current step:', state.step)
    dispatch({ type: "back" })
  }
  const next = () => {
    console.log('[Onboarding] Next clicked, current step:', state.step)
    dispatch({ type: "next" })
  }

  /**
   * Финиш онбординга: собираем Profile из state и сохраняем
   * в localStorage.
   */
  const finish = () => {
    const profile: Profile = {
      birthDate: state.birthDate,
      birthTime: state.birthTime,
      birthPlace: state.birthPlace,
      currentCity: selectEffectiveCurrentCity(state),
      sameAsBirth: state.sameAsBirth,
      birthdayCity: selectEffectiveBirthdayCity(state),
      birthdaySameAsCurrent: state.birthdaySameAsCurrent,
    }
    saveProfile(profile)
    onComplete()
  }

  return (
    <main className="h-dvh bg-background overflow-hidden">
      <div className="mx-auto flex h-dvh max-w-md flex-col border-x border-border/50 bg-background">
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
