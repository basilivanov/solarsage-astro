"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { Info } from "lucide-react"

import { listReadings } from "@/lib/api/readings"
import type { ComingReading } from "@/lib/readings"
import { AvailableCard } from "./available-card"
import { ComingCard } from "./coming-card"
import { InDevOverlay } from "./in-dev-overlay"

export function ReadingsScreen() {
  const router = useRouter()
  const { available, coming } = useMemo(() => listReadings(), [])
  const [devCard, setDevCard] = useState<ComingReading | null>(null)

  // Натальная карта подключена как полноценный экран — уходим на TOC.
  const openNatal = () => {
    router.push("/readings/natal")
  }

  const openHorary = () => {
    router.push("/readings/horary")
  }

  return (
    <div className="flex h-full w-full flex-col">
      <header
        className="flex flex-none flex-col gap-1 px-5 pb-5 pt-5"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1.25rem)" }}
      >
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Разборы
        </span>
        <h1 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
          Глубокие разборы
        </h1>
        <p className="text-pretty text-[13.5px] leading-relaxed text-muted-foreground">
          Персональные форматы по твоей карте и текущему периоду.
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-5 pb-8">
        {/* Инфо-плашка */}
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-border/60 bg-muted/40 px-4 py-3">
          <Info
            className="mt-0.5 h-4 w-4 flex-none text-muted-foreground/90"
            strokeWidth={1.6}
          />
          <p className="text-[12.5px] leading-relaxed text-muted-foreground">
            Не все форматы уже открыты — раздел будет постепенно расширяться.
          </p>
        </div>

        {/* Доступно сейчас */}
        <section aria-labelledby="readings-available">
          <div className="mb-3 flex items-baseline justify-between">
            <h2
              id="readings-available"
              className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground"
            >
              Доступно сейчас
            </h2>
            <span className="text-[11px] text-muted-foreground/70">
              {available.length}
            </span>
          </div>

          <div className="flex flex-col gap-3">
            {available.map((r) => (
              <AvailableCard
                key={r.key}
                icon={r.icon}
                title={r.title}
                description={r.description}
                teaser={r.teaser}
                onClick={r.key === "natal" ? openNatal : openHorary}
              />
            ))}
          </div>
        </section>

        {/* Скоро будет */}
        <section aria-labelledby="readings-coming" className="mt-8">
          <div className="mb-3 flex items-baseline justify-between">
            <h2
              id="readings-coming"
              className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground"
            >
              Скоро будет
            </h2>
            <span className="text-[11px] text-muted-foreground/70">
              {coming.length}
            </span>
          </div>

          <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
            {coming.map((r, i) => (
              <ComingCard
                key={r.key}
                icon={r.icon}
                title={r.title}
                description={r.description}
                isLast={i === coming.length - 1}
                onClick={() => setDevCard(r)}
              />
            ))}
          </div>
        </section>

        <p className="mt-8 text-center text-[12px] leading-relaxed text-muted-foreground/75">
          Форматы появляются постепенно — будем присылать уведомление, когда откроем новый.
        </p>
      </div>

      {devCard ? (
        <InDevOverlay
          icon={devCard.icon}
          title={devCard.title}
          description={devCard.description}
          onClose={() => setDevCard(null)}
        />
      ) : null}
    </div>
  )
}
