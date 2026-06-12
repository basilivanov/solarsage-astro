
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_STEP_WELCOME
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: step-welcome.tsx
// owns:
//   - components/onboarding/step-welcome.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { PrimaryCta } from "./primary-cta"

type Props = {
  onNext: () => void
  onSkip?: () => void
}

export function StepWelcome({ onNext, onSkip }: Props) {
  return (
    <div
      className="flex h-full w-full flex-col bg-background"
      style={{
        paddingTop: "max(env(safe-area-inset-top), 1rem)",
        paddingBottom: "max(env(safe-area-inset-bottom), 1rem)",
      }}
    >
      {/* Brand mark */}
      <div className="flex items-center justify-between px-5 pt-2">
        <span className="font-sans text-[11px] uppercase tracking-[0.22em] text-foreground/50">
          Lumen · Personal
        </span>
        <span className="font-serif text-[13px] italic text-foreground/40">
          Preview
        </span>
      </div>

      {/* Hero */}
      <div className="flex flex-1 flex-col justify-end px-5 pb-6">
        <div className="mb-10 h-px w-12 bg-accent/70" aria-hidden="true" />
        <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-accent">
          Персональный навигатор
        </p>
        <h1 className="mt-3 font-serif text-[44px] leading-[1.0] tracking-[-0.015em] text-foreground text-balance">
          Астрология как{" "}
          <span className="italic text-foreground/80">личная практика</span>,
          а не гороскоп.
        </h1>
        <p className="mt-5 max-w-[34ch] font-sans text-[15px] leading-relaxed text-foreground/60 text-pretty">
          Ежедневные разборы и точные подсказки, собранные по твоей карте
          и текущему дню. Без магии, без шума — только то, что важно именно
          сегодня.
        </p>

        {/* Value bullets */}
        <ul className="mt-8 space-y-3">
          {[
            "Точный расчёт под дату, время и место рождения",
            "Фокус дня, недели и годового фона",
            "Язык взрослого продукта, без эзотерических клише",
          ].map((line) => (
            <li
              key={line}
              className="flex items-start gap-3 font-sans text-[14px] leading-relaxed text-foreground/70"
            >
              <span
                className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent"
                aria-hidden="true"
              />
              {line}
            </li>
          ))}
        </ul>
      </div>

      <div className="px-5">
        <PrimaryCta label="Продолжить" onClick={onNext} />
        {onSkip ? (
          <button
            type="button"
            onClick={onSkip}
            className="mt-3 block w-full text-center font-sans text-[12px] text-foreground/45 underline-offset-4 transition hover:text-foreground/70 hover:underline"
          >
            Пропустить и сразу открыть приложение
          </button>
        ) : (
          <p className="mt-3 text-center font-sans text-[12px] text-foreground/45">
            Займёт меньше минуты · 5 коротких шагов
          </p>
        )}
      </div>
    </div>
  )
}
