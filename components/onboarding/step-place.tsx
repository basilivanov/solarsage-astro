"use client"

import { OnboardingShell } from "./onboarding-shell"
import { PrimaryCta } from "./primary-cta"
import { CityPicker } from "./city-picker"
import type { City } from "@/lib/contracts/city"

type Props = {
  birthPlace: City | null
  currentCity: City | null
  sameAsBirth: boolean
  onChangeBirthPlace: (_v: City | null) => void
  onChangeCurrentCity: (_v: City | null) => void
  onChangeSameAsBirth: (_v: boolean) => void
  onBack: () => void
  onNext: () => void
}

export function StepPlace({
  birthPlace,
  currentCity,
  sameAsBirth,
  onChangeBirthPlace,
  onChangeCurrentCity,
  onChangeSameAsBirth,
  onBack,
  onNext,
}: Props) {
  const birthValid = birthPlace !== null
  const currentValid =
    sameAsBirth || currentCity !== null
  const isValid = birthValid && currentValid

  return (
    <OnboardingShell
      step={2}
      total={3}
      onBack={onBack}
      eyebrow="Где это было"
      title="Место рождения"
      subtitle="Координаты влияют на расчёт домов и ключевых осей карты. Текущий город нужен для дневных переходов."
      footer={
        <PrimaryCta label="Далее" onClick={onNext} disabled={!isValid} />
      }
    >
      <div className="space-y-8">
        <div>
          <p className="mb-3 font-sans text-[11px] uppercase tracking-[0.14em] text-foreground/45">
            Город рождения
          </p>
          <CityPicker
            value={birthPlace}
            onChange={(city) => {
              onChangeBirthPlace(city)
              if (sameAsBirth) onChangeCurrentCity(city)
            }}
            placeholder="Например, Санкт-Петербург"
          />
        </div>

        <div>
          <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border/60 bg-card/60 p-4 transition active:bg-foreground/5">
            <span
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                sameAsBirth
                  ? "border-accent bg-accent"
                  : "border-border bg-background"
              }`}
              aria-hidden="true"
            >
              {sameAsBirth ? (
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
                Сейчас живу там же
              </span>
              <span className="mt-1 block font-sans text-[13px] leading-relaxed text-foreground/55">
                Использовать город рождения как текущий.
              </span>
            </span>
            <input
              type="checkbox"
              className="sr-only"
              checked={sameAsBirth}
              onChange={(e) => {
                onChangeSameAsBirth(e.target.checked)
                if (e.target.checked) onChangeCurrentCity(birthPlace)
              }}
            />
          </label>

          {!sameAsBirth ? (
            <div className="mt-5">
              <p className="mb-3 font-sans text-[11px] uppercase tracking-[0.14em] text-foreground/45">
                Текущий город
              </p>
              <CityPicker
                value={currentCity}
                onChange={onChangeCurrentCity}
                placeholder="Например, Лиссабон"
                autoFocus
              />
            </div>
          ) : null}
        </div>
      </div>
    </OnboardingShell>
  )
}

