"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { Sun, Moon } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

/**
 * ThemeToggle — animated light/dark mode switch.
 *
 * Uses next-themes to toggle the `.dark` class on `<html>`.
 * Renders a sun icon in light mode and a moon icon in dark mode,
 * with a smooth scale+rotate transition.
 *
 * Designed to sit in the Profile screen header or as a floating
 * action button. Mounts only on the client (avoids SSR flash).
 */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Avoid SSR hydration mismatch — render a placeholder until mounted
  if (!mounted) {
    return (
      <div
        className={`flex h-9 w-9 items-center justify-center rounded-full border border-border/60 ${className}`}
        aria-hidden
      />
    )
  }

  const current = resolvedTheme ?? theme ?? "light"
  const isDark = current === "dark"

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Включить светлую тему" : "Включить тёмную тему"}
      className={`relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full border border-border/60 bg-card transition active:scale-90 ${className}`}
    >
      <AnimatePresence mode="wait" initial={false}>
        {isDark ? (
          <motion.div
            key="moon"
            initial={{ scale: 0, rotate: -90, opacity: 0 }}
            animate={{ scale: 1, rotate: 0, opacity: 1 }}
            exit={{ scale: 0, rotate: 90, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
          >
            <Moon className="h-4 w-4 text-primary" strokeWidth={1.75} />
          </motion.div>
        ) : (
          <motion.div
            key="sun"
            initial={{ scale: 0, rotate: 90, opacity: 0 }}
            animate={{ scale: 1, rotate: 0, opacity: 1 }}
            exit={{ scale: 0, rotate: -90, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
          >
            <Sun className="h-4 w-4 text-amber-600" strokeWidth={1.75} />
          </motion.div>
        )}
      </AnimatePresence>
    </button>
  )
}
