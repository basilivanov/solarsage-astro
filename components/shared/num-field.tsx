
// ############################################################################
// AI_HEADER: MODULE_SHARED_NUM_FIELD
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: num-field.tsx
// owns:
//   - components/shared/num-field.tsx
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

import type { RefObject } from "react"

type NumFieldProps = {
  label: string
  placeholder: string
  value: string
  onChange: (_v: string) => void
  maxLength: number
  inputRef?: RefObject<HTMLInputElement | null>
  /** Расширенная колонка (например, год — 4 цифры). */
  wide?: boolean
  disabled?: boolean
}

/**
 * Числовое поле с верхним лейблом — используется в онбординге и в редакторах
 * профиля. Стрипает все нецифры, чтобы поле всегда оставалось валидным.
 */
export function NumField({
  label,
  placeholder,
  value,
  onChange,
  maxLength,
  inputRef,
  wide,
  disabled,
}: NumFieldProps) {
  return (
    <label className={`flex flex-col ${wide ? "flex-[1.6]" : "flex-1"}`}>
      <span className="font-sans text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </span>
      <input
        ref={inputRef}
        type="text"
        inputMode="numeric"
        placeholder={placeholder}
        maxLength={maxLength}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, ""))}
        className="mt-1 w-full border-b border-border bg-transparent pb-2 font-serif text-[26px] tracking-tight text-foreground placeholder:text-foreground/25 focus:border-accent focus:outline-none disabled:placeholder:text-foreground/15"
      />
    </label>
  )
}

/** Разделитель между числовыми полями (день·месяц·год). */
export function NumFieldDot() {
  return <span className="pb-2 font-serif text-[24px] text-foreground/25">·</span>
}

