
// ############################################################################
// AI_HEADER: MODULE_PROFILE_AVATAR
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for avatar.tsx behavior
// owns:
//   - components/profile/avatar.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import type { TelegramUser } from "@/hooks/use-telegram-user"

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
}

/**
 * Кружок аватара профиля. Если у пользователя есть фото из Telegram —
 * показываем его, иначе — инициалы по first/last name. Без аватарки и
 * без имени показываем "??", чтобы не было пустого круга.
 */
export function Avatar({ user }: { user: TelegramUser | null }) {
  const name = user
    ? [user.firstName, user.lastName].filter(Boolean).join(" ") || "Гость"
    : "Гость"
  const src = user?.photoUrl

  return (
    <div className="flex h-16 w-16 flex-none items-center justify-center overflow-hidden rounded-full border border-border/70 bg-accent/70 font-serif text-[22px] text-foreground/80">
      {src ? (
                <img
          src={src}
          alt={name}
          className="h-full w-full object-cover"
          referrerPolicy="no-referrer"
        />
      ) : (
        initials(name) || "??"
      )}
    </div>
  )
}
