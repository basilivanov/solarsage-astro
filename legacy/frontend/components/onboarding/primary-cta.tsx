"use client"

import type { ButtonHTMLAttributes } from "react"

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string
}

export function PrimaryCta({ label, disabled, className, ...rest }: Props) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={`flex h-14 w-full items-center justify-center rounded-2xl bg-accent font-sans text-[15px] font-medium tracking-[-0.005em] text-accent-foreground transition active:scale-[0.99] disabled:bg-foreground/10 disabled:text-foreground/40 ${className ?? ""}`}
      {...rest}
    >
      {label}
    </button>
  )
}
