"use client"

import type { ReactNode } from "react"
import { ArrowLeft } from "lucide-react"

type Props = {
  step?: number
  total?: number
  onBack?: () => void
  title: string
  subtitle?: string
  eyebrow?: string
  children: ReactNode
  footer: ReactNode
  showProgress?: boolean
}

export function OnboardingShell({
  step,
  total,
  onBack,
  title,
  subtitle,
  eyebrow,
  children,
  footer,
  showProgress = true,
}: Props) {
  return (
    <div className="flex h-full w-full flex-col bg-background">
      {/* Top bar */}
      <div
        className="flex items-center justify-between px-5 pb-2"
        style={{ paddingTop: "max(env(safe-area-inset-top), 0.75rem)" }}
      >
        <button
          type="button"
          onClick={onBack}
          aria-label="Назад"
          className={`-ml-1 flex h-9 w-9 items-center justify-center rounded-full text-foreground/70 transition ${
            onBack
              ? "hover:bg-foreground/5 active:bg-foreground/10"
              : "pointer-events-none opacity-0"
          }`}
        >
          <ArrowLeft className="h-5 w-5" strokeWidth={1.5} />
        </button>

        {showProgress && step && total ? (
          <div className="flex items-center gap-1.5" aria-hidden="true">
            {Array.from({ length: total }).map((_, i) => {
              const isDone = i < step - 1
              const isCurrent = i === step - 1
              return (
                <span
                  key={i}
                  className={`h-1 rounded-full transition-all ${
                    isCurrent
                      ? "w-6 bg-accent"
                      : isDone
                        ? "w-1.5 bg-foreground/40"
                        : "w-1.5 bg-foreground/15"
                  }`}
                />
              )
            })}
          </div>
        ) : (
          <div />
        )}

        {showProgress && step && total ? (
          <span className="font-sans text-[11px] uppercase tracking-[0.14em] text-foreground/45">
            {step} / {total}
          </span>
        ) : (
          <div className="w-9" />
        )}
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5 pt-6 pb-4">
        {eyebrow ? (
          <p className="mb-4 font-sans text-[11px] uppercase tracking-[0.18em] text-accent">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="font-serif text-[34px] leading-[1.05] tracking-[-0.01em] text-foreground text-balance">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-3 max-w-[32ch] font-sans text-[15px] leading-relaxed text-foreground/60 text-pretty">
            {subtitle}
          </p>
        ) : null}
        <div className="mt-8">{children}</div>
      </div>

      {/* Sticky footer */}
      <div
        className="border-t border-border/50 bg-background px-5 pt-3"
        style={{ paddingBottom: "max(env(safe-area-inset-bottom), 1rem)" }}
      >
        {footer}
      </div>
    </div>
  )
}
