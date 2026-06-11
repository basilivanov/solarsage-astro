
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_STEP_BIRTHDAY
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/onboarding/step-birthday.tsx
// owns:
//   - components/onboarding/step-birthday.tsx
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

import { OnboardingShell } from "./onboarding-shell"
import { PrimaryCta } from "./primary-cta"
import { CityPicker } from "./city-picker"
import type { City } from "@/lib/contracts/city"

type Props = {
  currentCity: City | null
  birthdayCity: City | null
  sameAsCurrent: boolean
  onChangeBirthdayCity: (_v: City | null) => void
  onChangeSameAsCurrent: (_v: boolean) => void
  onBack: () => void
  onNext: () => void
}

/**
 * Где пользователь встретит ближайший день рождения.
 * Если не совпадает с текущим городом — считаем соляр по другой локации.
 */
export function StepBirthday({
  currentCity,
  birthdayCity,
  sameAsCurrent,
  onChangeBirthdayCity,
  onChangeSameAsCurrent,
  onBack,
  onNext,
}: Props) {
  const isValid =
    sameAsCurrent || birthdayCity !== null

  return (
    <OnboardingShell
      step={3}
      total={3}
      onBack={onBack}
      eyebrow="Ближайший день рождения"
      title="Где встретишь свой день рождения?"
      subtitle="Это нужно для соляра — персонального прогноза на твой год. Если город совпадает с текущим, просто подтверди."
      footer={
        <PrimaryCta label="Далее" onClick={onNext} disabled={!isValid} />
      }
    >
      <div className="space-y-8">
        <div>
          <p className="mb-3 font-sans text-[11px] uppercase tracking-[0.14em] text-foreground/45">
            Текущий город
          </p>
          <p className="font-serif text-[22px] leading-tight tracking-tight text-foreground">
            {currentCity ? `${currentCity.name}, ${currentCity.country}` : "—"}
          </p>
        </div>

        <div>
          <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border/60 bg-card/60 p-4 transition active:bg-foreground/5">
            <span
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                sameAsCurrent
                  ? "border-accent bg-accent"
                  : "border-border bg-background"
              }`}
              aria-hidden="true"
            >
              {sameAsCurrent ? (
                <svg
                  className="h-3 w-3 text-accent-foreground"
                  viewBox="0 0 12 12"
                  fill="none"
                >
                  <path
                    d="M2.5 6.5L5 9L10 3.5"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : null}
            </span>
            <span>
              <span className="block font-sans text-[14px] font-medium text-foreground">
                Да, встречу там же
              </span>
              <span className="mt-1 block font-sans text-[13px] leading-relaxed text-foreground/55">
                Будем считать соляр по текущему городу.
              </span>
            </span>
            <input
              type="checkbox"
              className="sr-only"
              checked={sameAsCurrent}
              onChange={(e) => {
                onChangeSameAsCurrent(e.target.checked)
                if (e.target.checked) onChangeBirthdayCity(currentCity)
              }}
            />
          </label>

{!sameAsCurrent ? (
             <div className="mt-5">
               <p className="mb-3 font-sans text-[11px] uppercase tracking-[0.14em] text-foreground/45">
                 Город на день рождения
               </p>
               <CityPicker
                 value={birthdayCity}
                 onChange={onChangeBirthdayCity}
                 placeholder="Например, Берлин"
                 autoFocus
               />
             </div>
           ) : null}
        </div>
      </div>
    </OnboardingShell>
  )
}

