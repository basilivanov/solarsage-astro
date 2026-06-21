
// ############################################################################
// AI_HEADER: MODULE_PROFILE_DEV_MODE_SWITCHER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI dev-mode-switcher — component
// owns:
//   - components/profile/dev-mode-switcher.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useState } from "react"
import {
  Ban,
  Check,
  ChevronDown,
  Crown,
  Lock,
  RefreshCcw,
  Sparkles,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { AccessState } from "@/lib/access"

type DevOption = {
  key: AccessState
  icon: LucideIcon
  title: string
  description: string
}

const DEV_OPTIONS: DevOption[] = [
  {
    key: "trial",
    icon: Sparkles,
    title: "Триал · 14 дней",
    description: "Открыто окно 14 дней вперёд",
  },
  {
    key: "subscription",
    icon: Crown,
    title: "Подписка активна",
    description: "Прошлое и будущее открыты",
  },
  {
    key: "expired",
    icon: Lock,
    title: "Доступ истёк",
    description: "Окно закончилось — paywall",
  },
  {
    key: "none",
    icon: Ban,
    title: "Доступа нет",
    description: "Полный paywall везде",
  },
]

type Props = {
  currentState: AccessState
  onChangeState: (_state: AccessState) => void
  onResetOnboarding?: () => void
}

/**
 * Сворачиваемая dev-only секция в самом низу /profile.
 * Позволяет быстро переключать состояние доступа (triаl/sub/expired/none)
 * и сбрасывать онбординг — нужна, пока бэк-биллинг не подключен.
 *
 * При появлении реального биллинга — этот компонент удаляется,
 * `profile-screen.tsx` останется без изменений.
 */
export function DevModeSwitcher({
  currentState,
  onChangeState,
  onResetOnboarding,
}: Props) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-1 pb-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground transition active:text-foreground/70"
      >
        <span>Для разработчика</span>
        <ChevronDown
          className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
          strokeWidth={1.75}
        />
      </button>

      {open ? (
        <div className="space-y-3">
          <div className="overflow-hidden rounded-2xl border border-border/60 bg-card/70">
            {DEV_OPTIONS.map((opt, i) => {
              const Icon = opt.icon
              const isActive = currentState === opt.key
              return (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => onChangeState(opt.key)}
                  aria-pressed={isActive}
                  className={cn(
                    "flex w-full items-center gap-4 px-4 py-3.5 text-left transition active:bg-muted/50",
                    i !== DEV_OPTIONS.length - 1 && "border-b border-border/55",
                  )}
                >
                  <div
                    className={cn(
                      "flex h-9 w-9 flex-none items-center justify-center rounded-full",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "bg-accent/60 text-foreground/70",
                    )}
                  >
                    <Icon className="h-[17px] w-[17px]" strokeWidth={1.75} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[14px] font-medium leading-snug text-foreground">
                      {opt.title}
                    </div>
                    <div className="mt-0.5 truncate text-[12px] leading-snug text-muted-foreground">
                      {opt.description}
                    </div>
                  </div>
                  {isActive ? (
                    <Check
                      className="h-4 w-4 flex-none text-primary"
                      strokeWidth={2}
                    />
                  ) : (
                    <span className="h-4 w-4 flex-none" aria-hidden />
                  )}
                </button>
              )
            })}
          </div>

          {onResetOnboarding ? (
            <button
              type="button"
              onClick={onResetOnboarding}
              className="flex w-full items-center justify-center gap-2 rounded-full border border-border/60 bg-card/70 px-5 py-3 text-[13px] font-medium text-foreground/80 transition active:scale-[0.99]"
            >
              <RefreshCcw className="h-4 w-4" strokeWidth={1.75} />
              Пройти онбординг заново
            </button>
          ) : null}
        </div>
      ) : null}
    </>
  )
}

