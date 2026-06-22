
// ############################################################################
// AI_HEADER: MODULE_PROFILE_PROFILE_SCREEN
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for profile-screen.tsx behavior
// owns:
//   - components/profile/profile-screen.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useState } from "react"
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

import { AccessCard } from "./access-card"
import { Avatar } from "./avatar"
import { CheckinStatistics } from "./checkin-statistics"
import { DevModeSwitcher } from "./dev-mode-switcher"
import { EditSheet, type EditField } from "./edit-sheet"
import { HoraryCard } from "./horary-card"
import { ProfileRow } from "./profile-row"
import { ReferralCard } from "./referral-card"
import { ServiceRow } from "./service-row"
import { TransitTimeline } from "./transit-timeline"
import { LunarNodeWidget } from "./lunar-node-widget"
import { ThemeToggle } from "@/components/theme-toggle"

type Props = {
  access: AccessInfo
  currentState: AccessState
  profileMeta: ProfileMeta
  onChangeState: (_s: AccessState) => void
  onResetOnboarding?: () => void
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
export function ProfileScreen({
  access,
  currentState,
  profileMeta,
  onChangeState,
  onResetOnboarding,
}: Props) {
  const tgUser = useTelegramUser()
  const { profile, update } = useProfile()
  const [editField, setEditField] = useState<EditField | null>(null)

  const closeEdit = () => setEditField(null)

  const displayName = tgUser
    ? [tgUser.firstName, tgUser.lastName].filter(Boolean).join(" ")
    : "Гость"
  const handle = tgUser?.username ? `@${tgUser.username}` : "Telegram mini-app"

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto bg-background">
      {/* Header */}
      <header
        className="flex-none px-5 pb-5"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1.25rem)" }}
      >
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Профиль
          </span>
          <ThemeToggle />
        </div>
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

      <section className="px-5">
        <AccessCard
          access={access}
          currentState={currentState}
          onSubscribe={noop}
        />
      </section>

      <section className="px-5 pt-5">
        <ReferralCard referral={profileMeta.referral} />
      </section>

      <section className="px-5 pt-5">
        <HoraryCard horary={profileMeta.horary} />
      </section>

      {/* Статистика оценок (check-in) */}
      <CheckinStatistics />

      {/* Транзиты — ближайшие значимые аспекты */}
      <TransitTimeline />

      {/* Лунные узлы — Раху и Кету */}
      <LunarNodeWidget />

      {/* Мои данные */}
      <section className="px-5 pt-6">
        <h2 className="mb-2 px-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Мои данные
        </h2>
        <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
          <ProfileRow
            icon={Calendar}
            label="Дата рождения"
            value={formatBirthDate(profile.birthDate)}
            onClick={() => setEditField("birthDate")}
          />
          <ProfileRow
            icon={Clock}
            label="Время рождения"
            value={formatBirthTime(profile.birthTime)}
            onClick={() => setEditField("birthTime")}
          />
          <ProfileRow
            icon={MapPin}
            label="Место рождения"
            value={profile.birthPlace}
            onClick={() => setEditField("birthPlace")}
          />
          <ProfileRow
            icon={Home}
            label="Где живу сейчас"
            value={profile.currentCity}
            onClick={() => setEditField("currentCity")}
          />
          <ProfileRow
            icon={PartyPopper}
            label="Где проведу день рождения"
            value={profile.birthdayCity}
            onClick={() => setEditField("birthdayCity")}
            isLast
          />
        </div>
      </section>

      {/* Сервис */}
      <section className="px-5 pt-6">
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
            label="Управление подпиской"
            hint={
              currentState === "subscription"
                ? "Автопродление включено"
                : "Подписка не оформлена"
            }
            onClick={noop}
            isLast
          />
        </div>
      </section>

      <section className="px-5 pt-6 pb-10">
        <DevModeSwitcher
          currentState={currentState}
          onChangeState={onChangeState}
          onResetOnboarding={onResetOnboarding}
        />
      </section>

      {editField ? (
        <ProfileEditSheet
          field={editField}
          profile={profile}
          onSave={(patch) => {
            update(patch)
            closeEdit()
          }}
          onClose={closeEdit}
        />
      ) : null}
    </div>
  )
}

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
}: {
  field: EditField
  profile: Profile
  onSave: (_patch: Partial<Profile>) => void
  onClose: () => void
}) {
  switch (field) {
    case "birthDate":
      return (
        <EditSheet
          field="birthDate"
          initial={profile.birthDate}
          onClose={onClose}
          onSave={(v) => onSave({ birthDate: v })}
        />
      )
    case "birthTime":
      return (
        <EditSheet
          field="birthTime"
          initial={profile.birthTime}
          onClose={onClose}
          onSave={(v) => onSave({ birthTime: v })}
        />
      )
    case "birthPlace":
      return (
        <EditSheet
          field="birthPlace"
          initial={profile.birthPlace}
          onClose={onClose}
          onSave={(v) => onSave({ birthPlace: v })}
        />
      )
    case "currentCity":
      return (
        <EditSheet
          field="currentCity"
          initial={profile.currentCity}
          onClose={onClose}
          onSave={(v) => onSave({ currentCity: v })}
        />
      )
    case "birthdayCity":
      return (
        <EditSheet
          field="birthdayCity"
          initial={profile.birthdayCity}
          onClose={onClose}
          onSave={(v) => onSave({ birthdayCity: v })}
        />
      )
  }
}

