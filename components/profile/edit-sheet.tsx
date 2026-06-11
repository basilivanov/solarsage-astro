
// ############################################################################
// AI_HEADER: MODULE_PROFILE_EDIT_SHEET
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/profile/edit-sheet.tsx
// owns:
//   - components/profile/edit-sheet.tsx
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

import { useEffect, useRef, useState } from "react"
import { X } from "lucide-react"
import { CityPicker } from "@/components/onboarding/city-picker"
import { type City, formatCity } from "@/lib/contracts/city"
import { NumField, NumFieldDot } from "@/components/shared/num-field"
import {
  isValidBirthDate,
  isValidBirthTime,
  type BirthDateParts,
  type BirthTimeParts,
} from "@/lib/profile"

export type EditField =
  | "birthDate"
  | "birthTime"
  | "birthPlace"
  | "currentCity"
  | "birthdayCity"

type Props =
  | {
      field: "birthDate"
      initial: BirthDateParts
      onClose: () => void
      onSave: (_value: BirthDateParts) => void
    }
  | {
      field: "birthTime"
      initial: BirthTimeParts
      onClose: () => void
      onSave: (_value: BirthTimeParts) => void
    }
  | {
      field: "birthPlace" | "currentCity" | "birthdayCity"
      initial: string
      onClose: () => void
      onSave: (_value: string) => void
    }

const TITLES: Record<EditField, { eyebrow: string; title: string; subtitle: string }> = {
  birthDate: {
    eyebrow: "Когда ты родился",
    title: "Дата рождения",
    subtitle: "Основа персонального расчёта.",
  },
  birthTime: {
    eyebrow: "Время появления",
    title: "Время рождения",
    subtitle: "Можно пропустить — часть разборов останется точной.",
  },
  birthPlace: {
    eyebrow: "Где это было",
    title: "Место рождения",
    subtitle: "Координаты влияют на расчёт домов и осей карты.",
  },
  currentCity: {
    eyebrow: "Где ты сейчас",
    title: "Текущий город",
    subtitle: "Нужен для дневных переходов.",
  },
  birthdayCity: {
    eyebrow: "Как встретишь год",
    title: "Где проведёшь день рождения",
    subtitle: "Город на момент возвращения Солнца.",
  },
}

export function EditSheet(props: Props) {
  const { field, onClose } = props
  const meta = TITLES[field]
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  // Блокировка скролла body
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  const close = () => {
    setMounted(false)
    window.setTimeout(onClose, 220)
  }

  return (
    <div className="fixed inset-0 z-50" aria-modal="true" role="dialog">
      {/* Backdrop — на всю ширину экрана */}
      <button
        type="button"
        aria-label="Закрыть"
        onClick={close}
        className={`absolute inset-0 bg-black/40 transition-opacity duration-200 ${
          mounted ? "opacity-100" : "opacity-0"
        }`}
      />
      {/* Контейнер ограничен шириной приложения и центрирован */}
      <div className="pointer-events-none absolute inset-0 mx-auto flex max-w-md flex-col">
        {/* Sheet */}
        <div
          className={`pointer-events-auto relative mt-auto flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-3xl border-x border-t border-border/70 bg-background shadow-2xl transition-transform duration-200 ease-out ${
            mounted ? "translate-y-0" : "translate-y-full"
          }`}
        >
        <div className="mx-auto mt-2.5 h-1 w-10 flex-none rounded-full bg-border" />

        <div className="flex items-start justify-between px-5 pt-4">
          <div className="min-w-0 pr-3">
            <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {meta.eyebrow}
            </div>
            <h2 className="mt-1 font-serif text-[24px] leading-tight tracking-tight text-foreground">
              {meta.title}
            </h2>
            <p className="mt-1.5 text-[13px] leading-snug text-muted-foreground">
              {meta.subtitle}
            </p>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Закрыть"
            className="flex h-9 w-9 flex-none items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-6 pt-6">
          {props.field === "birthDate" ? (
            <DateEditor initial={props.initial} onSave={props.onSave} onClose={close} />
          ) : null}
          {props.field === "birthTime" ? (
            <TimeEditor initial={props.initial} onSave={props.onSave} onClose={close} />
          ) : null}
          {props.field === "birthPlace" ||
          props.field === "currentCity" ||
          props.field === "birthdayCity" ? (
            <CityEditor
              initial={props.initial}
              onSave={props.onSave}
              onClose={close}
            />
          ) : null}
        </div>
        </div>
      </div>
    </div>
  )
}

// ---------- Date ----------

function DateEditor({
  initial,
  onSave,
  onClose,
}: {
  initial: BirthDateParts
  onSave: (_v: BirthDateParts) => void
  onClose: () => void
}) {
  const [value, setValue] = useState<BirthDateParts>(initial)
  const monthRef = useRef<HTMLInputElement>(null)
  const yearRef = useRef<HTMLInputElement>(null)
  const valid = isValidBirthDate(value)

  return (
    <div className="space-y-8">
      <div>
        <p className="mb-3 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Дата
        </p>
        <div className="flex items-end gap-3">
          <NumField
            label="День"
            placeholder="ДД"
            maxLength={2}
            value={value.day}
            onChange={(day) => {
              setValue({ ...value, day })
              if (day.length === 2) monthRef.current?.focus()
            }}
          />
          <NumFieldDot />
          <NumField
            inputRef={monthRef}
            label="Месяц"
            placeholder="ММ"
            maxLength={2}
            value={value.month}
            onChange={(month) => {
              setValue({ ...value, month })
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
            value={value.year}
            onChange={(year) => setValue({ ...value, year })}
          />
        </div>
      </div>

      <SheetActions onCancel={onClose} onSave={() => onSave(value)} disabled={!valid} />
    </div>
  )
}

// ---------- Time ----------

function TimeEditor({
  initial,
  onSave,
  onClose,
}: {
  initial: BirthTimeParts
  onSave: (_v: BirthTimeParts) => void
  onClose: () => void
}) {
  const [value, setValue] = useState<BirthTimeParts>(initial)
  const minutesRef = useRef<HTMLInputElement>(null)
  const valid = isValidBirthTime(value)

  return (
    <div className="space-y-8">
      <div>
        <p className="mb-3 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Время
        </p>
        <div
          className={`flex items-end gap-4 transition ${
            value.unknown ? "opacity-35" : ""
          }`}
        >
          <NumField
            label="Часы"
            placeholder="ЧЧ"
            maxLength={2}
            value={value.hours}
            disabled={value.unknown}
            onChange={(hours) => {
              setValue({ ...value, hours })
              if (hours.length === 2) minutesRef.current?.focus()
            }}
          />
          <span className="pb-2 font-serif text-[28px] text-foreground/25">:</span>
          <NumField
            inputRef={minutesRef}
            label="Минуты"
            placeholder="ММ"
            maxLength={2}
            value={value.minutes}
            disabled={value.unknown}
            onChange={(minutes) => setValue({ ...value, minutes })}
          />
        </div>

        <label className="mt-4 flex cursor-pointer items-center gap-3">
          <span
            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
              value.unknown
                ? "border-accent bg-accent"
                : "border-border bg-background"
            }`}
            aria-hidden="true"
          >
            {value.unknown ? (
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
          <span className="text-[14px] text-foreground/75">Не знаю точное время</span>
          <input
            type="checkbox"
            className="sr-only"
            checked={value.unknown}
            onChange={(e) =>
              setValue({
                ...value,
                unknown: e.target.checked,
                hours: e.target.checked ? "" : value.hours,
                minutes: e.target.checked ? "" : value.minutes,
              })
            }
          />
        </label>
      </div>

      <SheetActions onCancel={onClose} onSave={() => onSave(value)} disabled={!valid} />
    </div>
  )
}

// ---------- City ----------

function CityEditor({
  initial,
  onSave,
  onClose,
}: {
  initial: string
  onSave: (_v: string) => void
  onClose: () => void
}) {
  const [city, setCity] = useState<City | null>(() => {
    if (!initial) return null
    const parts = initial.split(",")
    return {
      name: parts[0].trim(),
      country: parts[1]?.trim() || "",
    }
  })
  const valid = city !== null && city.name.trim().length >= 2

  return (
    <div className="space-y-8">
      <CityPicker
        value={city}
        onChange={setCity}
        placeholder="Начни вводить город"
      />
      <SheetActions
        onCancel={onClose}
        onSave={() => {
          if (city) {
            onSave(formatCity(city))
          }
        }}
        disabled={!valid}
      />
    </div>
  )
}

// ---------- Shared UI ----------

function SheetActions({
  onCancel,
  onSave,
  disabled,
}: {
  onCancel: () => void
  onSave: () => void
  disabled?: boolean
}) {
  return (
    <div
      className="flex gap-3 pt-2"
      style={{ paddingBottom: "max(env(safe-area-inset-bottom), 0.25rem)" }}
    >
      <button
        type="button"
        onClick={onCancel}
        className="flex h-12 flex-1 items-center justify-center rounded-full border border-border/70 bg-card text-[14px] font-medium text-foreground/75 transition active:scale-[0.99]"
      >
        Отменить
      </button>
      <button
        type="button"
        onClick={onSave}
        disabled={disabled}
        className="flex h-12 flex-[1.4] items-center justify-center rounded-full bg-foreground px-5 text-[14px] font-medium text-background transition active:scale-[0.99] disabled:opacity-40"
      >
        Сохранить
      </button>
    </div>
  )
}



