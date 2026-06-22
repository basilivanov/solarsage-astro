"use client"

import { ThemeProvider as NextThemesProvider } from "next-themes"
import type { ComponentProps } from "react"

/**
 * ThemeProvider — wraps next-themes to enable light/dark mode.
 *
 * The app's CSS (globals.css) already defines `.dark` class variables;
 * next-themes applies the `.dark` class to `<html>` when the theme is
 * "dark". `suppressHydrationWarning` on `<html>` (already set) handles
 * the SSR/client mismatch from the theme attribute.
 *
 * In demo mode, defaultTheme is "light" to match the warm-milk aesthetic.
 * The TelegramInit component also sets `.dark` on `<html>` when the
 * Telegram WebApp reports `colorScheme === "dark"` — this provider
 * respects that by using `enableSystem: false` (manual control only).
 */
export function ThemeProvider({
  children,
  ...props
}: ComponentProps<typeof NextThemesProvider>) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      disableTransitionOnChange
      {...props}
    >
      {children}
    </NextThemesProvider>
  )
}
