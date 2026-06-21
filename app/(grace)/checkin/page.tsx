"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { CheckinScreen } from "@/components/checkin/checkin-screen"
import { ArrowLeft } from "lucide-react"

export default function CheckinPage() {
  const router = useRouter()
  const [today] = useState(() => new Date().toISOString().split("T")[0])

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-md">
        <div className="flex items-center gap-3 px-5 pt-6">
          <button
            onClick={() => router.back()}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border/70"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <h1 className="font-serif text-[20px] text-foreground">Оценка дня</h1>
        </div>

        <CheckinScreen
          targetDate={today}
          onComplete={() => router.push("/day/today")}
        />
      </div>
    </main>
  )
}
