"use client"

import { useRouter } from "next/navigation"

export function ResetButton() {
  const router = useRouter()

  return (
    <button
      onClick={() => router.push("/reset")}
      className="mt-4 text-xs text-muted-foreground/50 underline hover:text-muted-foreground"
    >
      Сбросить кэш и сессию
    </button>
  )
}
