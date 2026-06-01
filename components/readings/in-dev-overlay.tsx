"use client"

import { useEffect, useState } from "react"
import { X, Hourglass, type LucideIcon } from "lucide-react"

type Props = {
  icon: LucideIcon
  title: string
  description: string
  onClose: () => void
}

export function InDevOverlay({ icon: Icon, title, description, onClose }: Props) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const t = window.setTimeout(() => setMounted(true), 10)
    return () => window.clearTimeout(t)
  }, [])

  function close() {
    setMounted(false)
    window.setTimeout(onClose, 180)
  }

  return (
    <div className="fixed inset-0 z-50" aria-modal="true" role="dialog">
      <button
        type="button"
        aria-label="Закрыть"
        onClick={close}
        className={`absolute inset-0 bg-black/40 transition-opacity duration-200 ${
          mounted ? "opacity-100" : "opacity-0"
        }`}
      />
      <div className="pointer-events-none absolute inset-0 mx-auto flex max-w-md flex-col">
        <div
          className={`pointer-events-auto relative mt-auto flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-3xl border-x border-t border-border/70 bg-background shadow-2xl transition-transform duration-200 ease-out ${
            mounted ? "translate-y-0" : "translate-y-full"
          }`}
        >
          <div
            className="flex items-center justify-between border-b border-border/60 px-5 py-4"
          >
            <div className="min-w-0">
              <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                В разработке
              </div>
              <h2 className="mt-0.5 truncate font-serif text-[20px] leading-tight tracking-tight text-foreground">
                {title}
              </h2>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Закрыть"
              className="flex h-9 w-9 flex-none items-center justify-center rounded-full text-foreground/60 transition active:scale-95 active:text-foreground"
            >
              <X className="h-5 w-5" strokeWidth={1.6} />
            </button>
          </div>

          <div className="flex flex-col items-center px-6 pb-8 pt-8 text-center">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Icon className="h-6 w-6" strokeWidth={1.5} />
            </div>
            <p className="max-w-[28ch] text-[14.5px] leading-relaxed text-foreground/80">
              {description}
            </p>

            <div className="mt-6 flex items-center gap-2 rounded-full border border-border/70 bg-card px-3.5 py-1.5 text-[11.5px] text-muted-foreground">
              <Hourglass className="h-3.5 w-3.5" strokeWidth={1.6} />
              <span>Готовим этот раздел — подожди немного</span>
            </div>

            <button
              type="button"
              onClick={close}
              className="mt-7 w-full rounded-xl border border-border/70 bg-card py-3 text-[14px] font-medium text-foreground/80 transition active:scale-[0.99]"
            >
              Понятно
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
