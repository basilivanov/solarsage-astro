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
        // eslint-disable-next-line @next/next/no-img-element
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
