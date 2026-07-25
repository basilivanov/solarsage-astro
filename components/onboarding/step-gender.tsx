
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_STEP_GENDER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT: M-ONBOARDING-STEP-GENDER
// purpose: Onboarding step component for gender selection ("male" | "female").
// owns:
//   - components/onboarding/step-gender.tsx
// inputs: gender ("male" | "female" | null), onSelect, onBack
// outputs: StepGender React component
// dependencies: OnboardingShell
// side_effects: none (pure UI step)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-ONBOARDING-STEP-GENDER

// START_MODULE_MAP: M-ONBOARDING-STEP-GENDER
// public_entrypoints:
//   - StepGender
// semantic_blocks:
//   - STEP_GENDER_COMPONENT: step gender selection component
// owned_tests:
//   - __tests__/components/OnboardingFlow.test.tsx
// END_MODULE_MAP: M-ONBOARDING-STEP-GENDER
"use client"

import { OnboardingShell } from "./onboarding-shell"

type Props = {
  gender: "male" | "female" | null
  onSelect: (_value: "male" | "female") => void
  onBack: () => void
}

// START_BLOCK: STEP_GENDER_COMPONENT
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
// END_BLOCK: STEP_GENDER_COMPONENT

