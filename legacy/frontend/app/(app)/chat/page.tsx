"use client"

import { ChatScreen } from "@/components/chat/chat-screen"
import { useProfile } from "@/hooks/use-profile"

/**
 * Маршрут /chat — пятая вкладка приложения.
 *
 * Профиль грузим тем же хуком, что и остальные экраны: данные хранятся
 * в localStorage и сюда приходят уже гидратированные. Пока профиль
 * не подгружен — ничего не рендерим (анти-мигание, как в AppShell).
 */
export default function ChatPage() {
  const { profile, loaded } = useProfile()
  if (!loaded) return null
  return <ChatScreen profile={profile} />
}
