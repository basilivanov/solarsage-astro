"use client"

import Link from "next/link"
import { ChevronLeft, Sparkles, HelpCircle } from "lucide-react"
import type { HoraryQuestion } from "@/lib/contracts/horary"
import { HORARY_CATEGORIES } from "@/lib/contracts/horary"
import { HoraryBlockRenderer } from "./horary-block-renderer"

type Props = {
  question: HoraryQuestion
}

const PLANET_RU: Record<string, string> = {
  Sun: "Солнце",
  Moon: "Луна",
  Mercury: "Меркурий",
  Venus: "Венера",
  Mars: "Марс",
  Jupiter: "Юпитер",
  Saturn: "Сатурн",
  Uranus: "Уран",
  Neptune: "Нептун",
  Pluto: "Плутон",
}

export function HoraryAnswerView({ question }: Props) {
  const { text, category, createdAt, answer, questionLocationName } = question

  if (!answer) return null

  const catMeta = HORARY_CATEGORIES.find((c) => c.key === category)

  const formatDisplayDate = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      {/* Header */}
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <Link
          href="/readings/horary"
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Хорарные вопросы</span>
        </Link>
      </header>

      <div className="flex-1 px-5 py-6 space-y-6 max-w-md mx-auto w-full">
        {/* Question Details */}
        <div className="rounded-2xl border border-border/60 bg-muted/20 p-5 space-y-3">
          <div className="flex items-center justify-between gap-2">
            {catMeta && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card px-2.5 py-0.5 text-[12px] text-foreground/85">
                <span>{catMeta.emoji}</span>
                <span>{catMeta.label}</span>
              </span>
            )}
            <span className="text-[12px] text-muted-foreground">
              {formatDisplayDate(createdAt)}
            </span>
          </div>
          <p className="font-serif text-[17px] italic leading-relaxed text-foreground/90">
            «{text}»
          </p>
          {questionLocationName && (
            <p className="text-[12.5px] text-muted-foreground flex items-center gap-1.5 pt-1.5 border-t border-border/40">
              <span className="font-sans font-medium uppercase text-[10px] tracking-wider text-muted-foreground/60">Место расчета:</span>
              <span>{questionLocationName}</span>
            </p>
          )}
        </div>

        {/* Blocks rendering (contains verdict_card as the first block in spec, but let's render blocks sequentially) */}
        <div className="space-y-5">
          {answer.blocks.map((block, i) => (
            <div key={i}>
              <HoraryBlockRenderer block={block} />
            </div>
          ))}
        </div>

        {/* Planets involved */}
        {answer.planets && answer.planets.length > 0 && (
          <div className="border-t border-border/40 pt-5 space-y-2.5">
            <h4 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Задействованные светила
            </h4>
            <div className="flex flex-wrap gap-2">
              {answer.planets.map((p) => {
                const ruName = PLANET_RU[p] || p
                return (
                  <span
                    key={p}
                    className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-card px-3 py-1 text-[13px] text-foreground/80"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/60" />
                    {ruName}
                  </span>
                )
              })}
            </div>
          </div>
        )}

        {/* Footer info */}
        <div className="text-center text-[12px] text-muted-foreground pt-8 pb-10">
          Сформировано {formatDisplayDate(answer.generatedAt)}
        </div>
      </div>
    </div>
  )
}
