
// ############################################################################
// AI_HEADER: MODULE_PROFILE_PROFILE_SCREEN
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT: M-PROFILE-PROFILE-SCREEN
// purpose: Profile screen composition hosting avatar, access card, referral, horary, and profile rows.
// owns:
//   - components/profile/profile-screen.tsx
// inputs: access, currentState, profileMeta, onAccessChanged
// outputs: ProfileScreen React component
// dependencies: useProfile, useTelegramUser, useSubscriptionPurchase, getSubscriptionStatus
// side_effects: fetches subscription status, updates profile fields via sheets
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-PROFILE-PROFILE-SCREEN

// START_MODULE_MAP: M-PROFILE-PROFILE-SCREEN
// public_entrypoints:
//   - ProfileScreen
// semantic_blocks:
//   - PROFILE_SCREEN_COMPONENT: main profile screen composition
// owned_tests:
//   - __tests__/components/ProfileScreen.test.tsx
//   - __tests__/components/ProfileScreen.cancel-refresh.test.tsx
// END_MODULE_MAP: M-PROFILE-PROFILE-SCREEN
"use client"

import { useEffect, useState } from "react"
import {
  Calendar,
  Clock,
  CreditCard,
  Home,
  LifeBuoy,
  MapPin,
  PartyPopper,
  Shield,
} from "lucide-react"

import type { AccessInfo, AccessState } from "@/lib/access"
import type { ProfileMeta } from "@/lib/profile-meta"
import { useProfile } from "@/hooks/use-profile"
import { useTelegramUser } from "@/hooks/use-telegram-user"
import { formatBirthDate, formatBirthTime, type Profile } from "@/lib/profile"
import {
  formatPriceRubles,
  useSubscriptionPurchase,
} from "@/lib/hooks/use-subscription-purchase"
import { getSubscriptionStatus } from "@/lib/api/payment"

import { AccessCard } from "./access-card"
import { Avatar } from "./avatar"
import { CheckinStatistics } from "./checkin-statistics"
import { EditSheet, type EditField } from "./edit-sheet"
import { HoraryCard } from "./horary-card"
import { CheckinStatsCard } from "./checkin-stats-card"
import { ProfileRow } from "./profile-row"
import { ReferralCard } from "./referral-card"
import { ServiceRow } from "./service-row"

type Props = {
  access: AccessInfo
  currentState: AccessState
  profileMeta: ProfileMeta
  onAccessChanged?: () => void
}

const noop = () => {
  /* stub */
}

/**
 * Экран /profile. Здесь только композиция — каждая секция вынесена
 * в отдельный файл (`avatar`, `referral-card`, `horary-card`,
 * `dev-mode-switcher`). Локальное состояние держит только то, что
 * относится именно к этому экрану: какое поле сейчас редактируется.
 */
// START_BLOCK: PROFILE_SCREEN_COMPONENT
export function ProfileScreen({
  access,
  currentState,
  profileMeta,
  onAccessChanged,
}: Props) {
  const tgUser = useTelegramUser()
  const { profile, update, loaded, saving, error } = useProfile()
  const [editField, setEditField] = useState<EditField | null>(null)
  const billingFlow = useSubscriptionPurchase(onAccessChanged)
  const [subFlags, setSubFlags] = useState<{ renewing: boolean; cancelable: boolean; status: string } | null>(null)

  useEffect(() => {
    // Renewal/cancel/enrollment semantics come from the BACKEND state machine
    // (SubscriptionStatusResponse.renewing/cancelable/status), never UI-derived.
    // billingFlow.statusRevision re-triggers this read after every
    // successful buy/cancel — flags never stay stale behind the ledger.
    if (currentState !== "subscription" || !billingFlow.ready || billingFlow.unavailable) {
      setSubFlags(null)
      return
    }
    let cancelled = false
    getSubscriptionStatus()
      .then((status) => {
        if (!cancelled) {
          setSubFlags({ renewing: status.renewing, cancelable: status.cancelable, status: status.status })
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [currentState, billingFlow.ready, billingFlow.unavailable, billingFlow.statusRevision])

  const billingBusy = billingFlow.phase === "starting" || billingFlow.phase === "waiting"
  const billing = {
    ready: billingFlow.ready,
    unavailable: billingFlow.unavailable,
    busy: billingBusy,
    monthLabel: billingFlow.month
      ? `Подписка · ${formatPriceRubles(billingFlow.month.priceKopecks)} ₽/мес`
      : "Подписка",
    yearLabel: billingFlow.year
      ? `Подписка · ${formatPriceRubles(billingFlow.year.priceKopecks)} ₽/год`
      : "Подписка на год",
    // Recurring-consent copy shown BEFORE the buy click (save-during-payment
    // scheme): exact amount/period of auto-renewal from the API catalog and
    // how to cancel. Never a legal wall of text.
    consent: billingFlow.month && billingFlow.year
      ? `Подписка с автопродлением: ${formatPriceRubles(billingFlow.month.priceKopecks)} ₽ каждый месяц или ${formatPriceRubles(billingFlow.year.priceKopecks)} ₽ в год. Отменить можно в любой момент в профиле — уже оплаченный период сохранится.`
      : null,
    onBuy: (slug: "subscription_month" | "subscription_year") => void billingFlow.buy(slug),
    onCancel: () => void billingFlow.cancel(),
  }

  const closeEdit = () => setEditField(null)

  const displayName = tgUser
    ? [tgUser.firstName, tgUser.lastName].filter(Boolean).join(" ")
    : "Гость"
  const handle = tgUser?.username ? `@${tgUser.username}` : "Telegram mini-app"

  // Hydration-first: loaded → "ready" even if error contains a later save error
  const screenState = loaded ? "ready" : error ? "error" : "loading"

  return (
    <div
      className="flex h-full w-full flex-col overflow-y-auto bg-background"
      data-testid="profile-screen"
      data-state={screenState}
      data-access-state={currentState}
    >
      {/* Header */}
      <header
        className="flex-none px-5 pb-5"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1.25rem)" }}
        data-testid="profile-header"
      >
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Профиль
        </span>
        <div className="mt-3 flex items-center gap-4">
          <Avatar user={tgUser} />
          <div className="min-w-0 flex-1">
            <div className="truncate font-serif text-[22px] leading-tight tracking-tight text-foreground">
              {displayName || "Гость"}
            </div>
            <div className="mt-0.5 truncate text-[13px] text-muted-foreground">
              {handle}
            </div>
          </div>
        </div>
      </header>

      <section className="scroll-mt-6 px-5" id="credits" data-testid="profile-access-card">
        <AccessCard
          access={access}
          currentState={currentState}
          billing={billing}
          renewal={subFlags === null ? undefined : subFlags}
        />
        {billingFlow.errorMessage ? (
          <p className="mt-2 px-1 text-[12px] text-destructive" role="alert" data-testid="profile-billing-error">
            {billingFlow.errorMessage}
          </p>
        ) : null}
      </section>

      <section className="px-5 pt-5" data-testid="profile-referral-card">
        <ReferralCard referral={profileMeta.referral} />
      </section>

      <section className="px-5 pt-5" data-testid="profile-horary-card">
        <HoraryCard horary={profileMeta.horary} />
      </section>

      <section className="px-5 pt-5">
        <CheckinStatsCard />
      </section>

      <CheckinStatistics
        timeZone={
          profile.currentLocation?.timezone || profile.birthLocation?.timezone || null
        }
      />

      {/* Мои данные */}
      <section className="px-5 pt-6" data-testid="profile-data-section">
        <h2 className="mb-2 px-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Мои данные
        </h2>
        {!loaded ? (
          <p
            className="mb-2 px-1 text-[12px] text-muted-foreground"
            role={error ? "alert" : "status"}
          >
            {error ? `Не удалось загрузить профиль: ${error}` : "Загружаем данные профиля..."}
          </p>
        ) : null}
        <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
          <ProfileRow
            icon={Calendar}
            label="Дата рождения"
            value={formatBirthDate(profile.birthDate)}
            onClick={() => setEditField("birthDate")}
            disabled={!loaded}
            testId="profile-data-row-birth-date"
          />
          <ProfileRow
            icon={Clock}
            label="Время рождения"
            value={formatBirthTime(profile.birthTime)}
            onClick={() => setEditField("birthTime")}
            disabled={!loaded}
            testId="profile-data-row-birth-time"
          />
          <ProfileRow
            icon={MapPin}
            label="Место рождения"
            value={profile.birthPlace}
            onClick={() => setEditField("birthPlace")}
            disabled={!loaded}
            testId="profile-data-row-birth-place"
          />
          <ProfileRow
            icon={Home}
            label="Где живу сейчас"
            value={profile.currentCity}
            onClick={() => setEditField("currentCity")}
            disabled={!loaded}
            testId="profile-data-row-current-city"
          />
          <ProfileRow
            icon={PartyPopper}
            label="Где проведу день рождения"
            value={profile.birthdayCity}
            onClick={() => setEditField("birthdayCity")}
            disabled={!loaded}
            isLast
            testId="profile-data-row-birthday-city"
          />
        </div>
      </section>

      {/* Сервис */}
      <section className="px-5 pt-6" data-testid="profile-service-section">
        <h2 className="mb-2 px-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Сервис
        </h2>
        <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
          <ServiceRow icon={LifeBuoy} label="Поддержка" onClick={noop} />
          <ServiceRow
            icon={Shield}
            label="Условия и конфиденциальность"
            onClick={noop}
          />
          <ServiceRow
            icon={CreditCard}
            label="Платежи"
            hint={billingFlow.unavailable ? "Оплата временно недоступна" : "Подписка и управление оплатой"}
            onClick={() =>
              document
                .querySelector('[data-testid="profile-access-card"]')
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
            isLast
          />
        </div>
      </section>

      {editField && loaded ? (
        <ProfileEditSheet
          field={editField}
          profile={profile}
          saving={saving}
          error={error}
          onSave={async (patch) => {
            await update(patch)
            closeEdit()
          }}
          onClose={closeEdit}
        />
      ) : null}
    </div>
  )
}

// END_BLOCK: PROFILE_SCREEN_COMPONENT

/**
 * Тонкая обёртка над `EditSheet`, которая по `field` подставляет нужный
 * `initial` из текущего профиля и узкий patch в `onSave`. Раньше эти
 * пять веток лежали в JSX — теперь это один switch на типобезопасном
 * discriminated union.
 */
function ProfileEditSheet({
  field,
  profile,
  onSave,
  onClose,
  saving,
  error,
}: {
  field: EditField
  profile: Profile
  onSave: (_patch: Partial<Profile>) => void | Promise<void>
  onClose: () => void
  saving?: boolean
  error?: string | null
}) {
  switch (field) {
    case "birthDate":
      return (
        <EditSheet
          field="birthDate"
          initial={profile.birthDate}
          onClose={onClose}
          onSave={(v) => onSave({ birthDate: v })}
          saving={saving}
          error={error}
        />
      )
    case "birthTime":
      return (
        <EditSheet
          field="birthTime"
          initial={profile.birthTime}
          onClose={onClose}
          onSave={(v) => onSave({ birthTime: v })}
          saving={saving}
          error={error}
        />
      )
    case "birthPlace":
      return (
        <EditSheet
          field="birthPlace"
          initial={profile.birthLocation}
          onClose={onClose}
          onSave={(v) => onSave({ birthPlace: v.city, birthLocation: v })}
          saving={saving}
          error={error}
        />
      )
    case "currentCity":
      return (
        <EditSheet
          field="currentCity"
          initial={profile.currentLocation}
          onClose={onClose}
          onSave={(v) => onSave({ currentCity: v.city, currentLocation: v })}
          saving={saving}
          error={error}
        />
      )
    case "birthdayCity":
      return (
        <EditSheet
          field="birthdayCity"
          initial={profile.birthdayLocation}
          onClose={onClose}
          onSave={(v) => onSave({ birthdayCity: v.city, birthdayLocation: v })}
          saving={saving}
          error={error}
        />
      )
  }
}
