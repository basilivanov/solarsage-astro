
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_STEP_BIRTH
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/onboarding/step-birth.tsx
// owns:
//   - components/onboarding/step-birth.tsx
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

import { useRef } from "react"
import { OnboardingShell } from "./onboarding-shell"
import { PrimaryCta } from "./primary-cta"
import { NumField, NumFieldDot } from "@/components/shared/num-field"
import {
  isValidBirthDate,
  isValidBirthTime,
  type BirthDateParts,
  type BirthTimeParts,
} from "@/lib/profile"

// Алиасы оставлены для обратной совместимости с onboarding-flow,
// но опираются на единый источник типа из lib/profile.
export type BirthDate = BirthDateParts
export type BirthTime = BirthTimeParts

type Props = {
  date: BirthDate
  time: BirthTime
  onChangeDate: (_v: BirthDate) => void
  onChangeTime: (_v: BirthTime) => void
  onBack: () => void
  onNext: () => void
}

export function StepBirth({
  date,
  time,
  onChangeDate,
  onChangeTime,
  onBack,
  onNext,
}: Props) {
  const monthRef = useRef<HTMLInputElement>(null)
  const yearRef = useRef<HTMLInputElement>(null)
  const hoursRef = useRef<HTMLInputElement>(null)
  const minutesRef = useRef<HTMLInputElement>(null)

  const isValid = isValidBirthDate(date) && isValidBirthTime(time)

  return (
    <OnboardingShell
      step={1}
      total={3}
      onBack={onBack}
      eyebrow="Когда ты родился"
      title="Дата и время рождения"
      subtitle="Основа персонального расчёта. Время можно пропустить — часть разборов всё равно останется точной."
      footer={<PrimaryCta label="Далее" onClick={onNext} disabled={!isValid} />}
    >
      <div className="space-y-8">
        <div>
          <p className="mb-3 font-sans text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Дата
          </p>
          <div className="flex items-end gap-3">
            <NumField
              label="День"
              placeholder="ДД"
              maxLength={2}
              value={date.day}
              onChange={(day) => {
                onChangeDate({ ...date, day })
                if (day.length === 2) monthRef.current?.focus()
              }}
            />
            <NumFieldDot />
            <NumField
              inputRef={monthRef}
              label="Месяц"
              placeholder="ММ"
              maxLength={2}
              value={date.month}
              onChange={(month) => {
                onChangeDate({ ...date, month })
                if (month.length === 2) yearRef.current?.focus()
              }}
            />
            <NumFieldDot />
            <NumField
              inputRef={yearRef}
              label="Год"
              placeholder="ГГГГ"
              maxLength={4}
              wide
              value={date.year}
              onChange={(year) => {
                onChangeDate({ ...date, year })
                if (year.length === 4) hoursRef.current?.focus()
              }}
            />
          </div>
        </div>

        <div>
          <p className="mb-3 font-sans text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Время
          </p>
          <div
            className={`flex items-end gap-4 transition ${time.unknown ? "opacity-35" : ""}`}
          >
            <NumField
              inputRef={hoursRef}
              label="Часы"
              placeholder="ЧЧ"
              maxLength={2}
              value={time.hours}
              disabled={time.unknown}
              onChange={(hours) => {
                onChangeTime({ ...time, hours })
                if (hours.length === 2) minutesRef.current?.focus()
              }}
            />
            <span className="pb-2 font-serif text-[28px] text-foreground/25">
              :
            </span>
            <NumField
              inputRef={minutesRef}
              label="Минуты"
              placeholder="ММ"
              maxLength={2}
              value={time.minutes}
              disabled={time.unknown}
              onChange={(minutes) => onChangeTime({ ...time, minutes })}
            />
          </div>

          <label className="mt-4 flex cursor-pointer items-center gap-3">
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                time.unknown
                  ? "border-accent bg-accent"
                  : "border-border bg-background"
              }`}
              aria-hidden="true"
            >
              {time.unknown ? (
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
            <span className="font-sans text-[14px] text-foreground/75">
              Не знаю точное время
            </span>
            <input
              type="checkbox"
              className="sr-only"
              checked={time.unknown}
              onChange={(e) =>
                onChangeTime({
                  ...time,
                  unknown: e.target.checked,
                  hours: e.target.checked ? "" : time.hours,
                  minutes: e.target.checked ? "" : time.minutes,
                })
              }
            />
          </label>
        </div>
      </div>
    </OnboardingShell>
  )
}

