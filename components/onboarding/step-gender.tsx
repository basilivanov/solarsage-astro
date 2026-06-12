
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_STEP_GENDER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: step-gender.tsx
// owns:
//   - components/onboarding/step-gender.tsx
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

import { OnboardingShell } from "./onboarding-shell"

type Props = {
  gender: "male" | "female" | null
  onSelect: (_value: "male" | "female") => void
  onBack: () => void
}

export function StepGender({ gender, onSelect, onBack }: Props) {
  return (
    <OnboardingShell
      step={4}
      total={4}
      onBack={onBack}
      eyebrow="Немного о тебе"
      title="Ты мужчина или женщина?"
      subtitle="Это нужно для персонализации интерпретаций и языка разборов."
      footer={<div />}
    >
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => onSelect("male")}
          className={`w-full rounded-2xl border p-5 text-left transition active:scale-[0.99] ${
            gender === "male"
              ? "border-accent bg-accent/10"
              : "border-border/60 bg-card/60 active:bg-foreground/5"
          }`}
        >
          <span className="block font-serif text-[24px] tracking-tight text-foreground">
            Мужчина
          </span>
        </button>

        <button
          type="button"
          onClick={() => onSelect("female")}
          className={`w-full rounded-2xl border p-5 text-left transition active:scale-[0.99] ${
            gender === "female"
              ? "border-accent bg-accent/10"
              : "border-border/60 bg-card/60 active:bg-foreground/5"
          }`}
        >
          <span className="block font-serif text-[24px] tracking-tight text-foreground">
            Женщина
          </span>
        </button>
      </div>
    </OnboardingShell>
  )
}

