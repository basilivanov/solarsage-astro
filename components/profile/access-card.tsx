
// ############################################################################
// AI_HEADER: MODULE_PROFILE_ACCESS_CARD
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: access-card.tsx
// owns:
//   - components/profile/access-card.tsx
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

import type { LucideIcon } from "lucide-react"
import { Sparkles, Crown, Lock, Ban, ArrowRight, Gift } from "lucide-react"
import type { AccessInfo, AccessState } from "@/lib/access"
import { formatLong } from "@/lib/date"
import { cn } from "@/lib/utils"
import { useShareInvite } from "@/lib/hooks/use-share-invite"

type Props = {
  access: AccessInfo
  currentState: AccessState
  billing?: AccessCardBilling
  renewal?: { renewing: boolean; cancelable: boolean }
}

export type AccessCardBilling = {
  ready: boolean
  unavailable: boolean
  busy: boolean
  monthLabel: string
  yearLabel: string
  onBuy: (_slug: "subscription_month" | "subscription_year") => void
  onCancel: () => void
}

type Variant = {
  icon: LucideIcon
  tone: "active" | "muted"
  label: string
  title: string
  subtitle: string
  footnote: string
  primary: { label: string; onClick?: () => void; icon?: LucideIcon; disabled?: boolean }
  secondary: { label: string; onClick?: () => void; icon?: LucideIcon; disabled?: boolean }
}

function subscribeButtons(billing: AccessCardBilling): Pick<Variant, "primary" | "secondary"> {
  if (billing.busy) {
    return {
      primary: { label: "Ждём подтверждение оплаты…", disabled: true },
      secondary: { label: billing.yearLabel, disabled: true },
    }
  }
  return {
    primary: { label: billing.monthLabel, onClick: () => billing.onBuy("subscription_month"), icon: ArrowRight },
    secondary: { label: billing.yearLabel, onClick: () => billing.onBuy("subscription_year") },
  }
}

function buildVariant(
  access: AccessInfo,
  state: AccessState,
  billing: AccessCardBilling | undefined,
  onInvite?: () => void,
  renewal?: { renewing: boolean; cancelable: boolean },
): Variant {
  const unavailableButtons: Pick<Variant, "primary" | "secondary"> = {
    primary: { label: billing?.ready === false && !billing.unavailable ? "Загружаем тарифы…" : "Оплата временно недоступна", disabled: true },
    secondary: { label: "Пригласить друга", onClick: onInvite, icon: Gift },
  }
  if (state === "trial") {
    const days = access.daysLeft
    const ending =
      access.accessEnd && `до ${formatLong(access.accessEnd)}`
    return {
      icon: Sparkles,
      tone: "active",
      label: "Доступ",
      title: "Доступ активен",
      subtitle: `Осталось ${days} ${pluralDays(days)}${ending ? ` · ${ending}` : ""}`,
      footnote:
        "Сначала расходуются бонусные дни. Подписка продлит доступ без перерыва.",
      ...(billing && !billing.unavailable && billing.ready ? subscribeButtons(billing) : unavailableButtons),
    }
  }

  if (state === "subscription") {
    const ending = access.accessEnd ? `до ${formatLong(access.accessEnd)}` : ""
    const footnote = renewal
      ? renewal.renewing
        ? "Автопродление активно. Отмена подписки не отзывает уже оплаченный период."
        : "Без автопродления — доступ до конца оплаченного периода. Новую подписку можно оформить после его завершения."
      : "Доступ активен. Отмена подписки не отзывает уже оплаченный период."
    // The cancel button exists ONLY for a real recurring enrollment
    // (backend cancelable). Non-renewing subscriptions have nothing to
    // cancel recurrently.
    const showCancel =
      billing && !billing.unavailable && billing.ready && renewal?.cancelable === true
    return {
      icon: Crown,
      tone: "active",
      label: "Доступ",
      title: "Подписка активна",
      subtitle: ending || "Доступ к прошлому и будущему",
      footnote,
      primary: { label: "Пригласить друга", onClick: onInvite, icon: Gift },
      secondary: showCancel
        ? { label: billing.busy ? "Ждём подтверждение…" : "Отменить подписку", onClick: billing.busy ? undefined : billing.onCancel, disabled: billing.busy }
        : { label: "Пригласить друга", onClick: onInvite, icon: Gift },
    }
  }

  if (state === "expired") {
    return {
      icon: Lock,
      tone: "muted",
      label: "Доступ",
      title: "Доступ закончился",
      subtitle: access.accessEnd
        ? `Окно закрылось ${formatLong(access.accessEnd)}`
        : "Окно доступа завершилось",
      footnote:
        "Продли доступ подпиской — или пригласи друга и получите бонусные дни.",
      ...(billing && !billing.unavailable && billing.ready ? subscribeButtons(billing) : unavailableButtons),
    }
  }

  return {
    icon: Ban,
    tone: "muted",
    label: "Доступ",
    title: "Нет доступа",
    subtitle: "Разборы дней закрыты",
    footnote:
      "Открой доступ подпиской — или пригласи друга: вы оба получите 14 дней бесплатно.",
    ...(billing && !billing.unavailable && billing.ready ? subscribeButtons(billing) : unavailableButtons),
  }
}

function pluralDays(n: number) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "день"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "дня"
  return "дней"
}

export function AccessCard({ access, currentState, billing, renewal }: Props) {
  const share = useShareInvite()
  const v = buildVariant(access, currentState, billing, share, renewal)
  const Icon = v.icon
  const PrimaryIcon = v.primary.icon
  const SecondaryIcon = v.secondary.icon

  return (
    <div
      className={cn(
        "rounded-2xl border bg-card p-5",
        v.tone === "active" ? "border-border/70" : "border-border/60",
      )}
      data-billing={billing ? (billing.busy ? "busy" : billing.unavailable ? "unavailable" : billing.ready ? "ready" : "loading") : "off"}
      data-renewal={renewal ? (renewal.renewing ? "renewing" : "non-renewing") : undefined}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-10 w-10 flex-none items-center justify-center rounded-full",
            v.tone === "active"
              ? "bg-primary/10 text-primary"
              : "bg-muted text-muted-foreground",
          )}
        >
          <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {v.label}
          </div>
          <div className="mt-1 font-serif text-[22px] leading-tight tracking-tight text-foreground">
            {v.title}
          </div>
          <div className="mt-1 text-[13px] leading-snug text-muted-foreground">
            {v.subtitle}
          </div>
        </div>
      </div>

      <p className="mt-4 text-[12.5px] leading-relaxed text-foreground/65">
        {v.footnote}
      </p>

      <div className="mt-4 flex flex-col gap-2">
        <button
          type="button"
          onClick={v.primary.disabled ? undefined : v.primary.onClick}
          disabled={v.primary.disabled}
          aria-disabled={v.primary.disabled}
          data-testid="access-card-primary"
          className="flex h-11 items-center justify-center gap-2 rounded-full bg-primary px-5 text-[14px] font-medium text-primary-foreground transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100"
        >
          {v.primary.label}
          {PrimaryIcon ? (
            <PrimaryIcon className="h-4 w-4" strokeWidth={2} />
          ) : null}
        </button>
        <button
          type="button"
          onClick={v.secondary.disabled ? undefined : v.secondary.onClick}
          disabled={v.secondary.disabled}
          aria-disabled={v.secondary.disabled}
          data-testid="access-card-secondary"
          className="flex h-11 items-center justify-center gap-2 rounded-full border border-border/70 bg-card px-5 text-[13.5px] font-medium text-foreground/85 transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100"
        >
          {SecondaryIcon ? (
            <SecondaryIcon className="h-4 w-4" strokeWidth={1.75} />
          ) : null}
          {v.secondary.label}
        </button>
      </div>
    </div>
  )
}
