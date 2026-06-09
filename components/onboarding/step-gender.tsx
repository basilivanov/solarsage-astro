"use client"

import { OnboardingShell } from "./onboarding-shell"

type Props = {
  gender: "male" | "female" | null
  onSelect: (value: "male" | "female") => void
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
