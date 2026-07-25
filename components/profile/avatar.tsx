
// ############################################################################
// AI_HEADER: MODULE_PROFILE_AVATAR
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT: M-PROFILE-AVATAR
// purpose: Render profile avatar image or user name initials circle.
// owns:
//   - components/profile/avatar.tsx
// inputs: user (TelegramUser | null)
// outputs: Avatar React component
// dependencies: hooks/use-telegram-user
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-PROFILE-AVATAR

// START_MODULE_MAP: M-PROFILE-AVATAR
// public_entrypoints:
//   - Avatar
// semantic_blocks:
//   - AVATAR_COMPONENT: profile avatar component
// owned_tests:
//   - __tests__/components/ProfileScreen.test.tsx
// END_MODULE_MAP: M-PROFILE-AVATAR
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
// START_BLOCK: AVATAR_COMPONENT
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
// END_BLOCK: AVATAR_COMPONENT
