"use client"

import type { LucideIcon } from "lucide-react"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

type Props = {
  icon: LucideIcon
  label: string
  value?: string
  placeholder?: string
  onClick?: () => void
  className?: string
  isLast?: boolean
}

export function ProfileRow({
  icon: Icon,
  label,
  value,
  placeholder = "Не указано",
  onClick,
  className,
  isLast = false,
}: Props) {
  const filled = Boolean(value)
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-4 px-4 py-3.5 text-left transition active:bg-muted/50",
        !isLast && "border-b border-border/55",
        className,
      )}
    >
      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-accent/60 text-foreground/75">
        <Icon className="h-[17px] w-[17px]" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </div>
        <div
          className={cn(
            "mt-0.5 truncate text-[14.5px] leading-snug",
            filled ? "text-foreground" : "text-foreground/45",
          )}
        >
          {filled ? value : placeholder}
        </div>
      </div>
      <ChevronRight
        className="h-4 w-4 flex-none text-muted-foreground/60"
        strokeWidth={1.75}
      />
    </button>
  )
}
