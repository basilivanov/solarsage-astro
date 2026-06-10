"use client"

import { Sparkles } from "lucide-react"

type Props = {
  priceKopecks: number
  disabled?: boolean
  onClick?: () => void
}

export function CtaButton({ priceKopecks, disabled, onClick }: Props) {
  const price = Math.round(priceKopecks / 100)

  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className="group relative w-full overflow-hidden rounded-2xl bg-primary px-4 py-4 text-center transition active:scale-[0.99] disabled:active:scale-100"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-primary to-primary/90" />
        <div className="relative flex items-center justify-center gap-2">
          <Sparkles className="h-4 w-4 text-primary-foreground/80" />
          <span className="text-[16px] font-semibold text-primary-foreground">
            Полный отчёт за {price} ₽
          </span>
        </div>
        {disabled ? (
          <div className="absolute inset-0 flex items-center justify-center bg-primary/70 backdrop-blur-[1px]">
            <span className="text-[13px] font-medium text-primary-foreground/80">Скоро</span>
          </div>
        ) : null}
      </button>
      <p className="text-center text-[11px] text-muted-foreground/60">
        Разбор по точным данным рождения · 8 глав
      </p>
    </div>
  )
}
