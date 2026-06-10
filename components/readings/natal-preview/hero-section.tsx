"use client"

import { Sparkles } from "lucide-react"

type Props = {
  name?: string | null
  ascSign?: string | null
  sunSign?: string | null
  moonSign?: string | null
  birthCity?: string | null
}

const SIGN_RU: Record<string, string> = {
  Aries: "Овне", Taurus: "Тельце", Gemini: "Близнецах",
  Cancer: "Раке", Leo: "Льве", Virgo: "Деве",
  Libra: "Весах", Scorpio: "Скорпионе", Sagittarius: "Стрельце",
  Capricorn: "Козероге", Aquarius: "Водолее", Pisces: "Рыбах",
}

export function HeroSection({ name, ascSign, sunSign, moonSign, birthCity }: Props) {
  const ascLabel = ascSign ? SIGN_RU[ascSign] ?? ascSign : null
  const sunLabel = sunSign ? SIGN_RU[sunSign] ?? sunSign : null
  const moonLabel = moonSign ? SIGN_RU[moonSign] ?? moonSign : null

  const badges = [
    ascLabel ? { label: `ASC в ${ascLabel}` } : null,
    sunLabel ? { label: `Солнце в ${sunLabel}` } : null,
    moonLabel ? { label: `Луна в ${moonLabel}` } : null,
  ].filter(Boolean) as { label: string }[]

  return (
    <section className="rounded-3xl border border-border/70 bg-card px-5 py-6">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 flex-none items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="font-serif text-[28px] leading-tight tracking-tight text-foreground">
            Твоя натальная карта
          </h1>
          <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">
            Твой характер, отношения, сильные стороны и внутренние сценарии — по точным данным рождения.
          </p>
        </div>
      </div>

      {badges.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {badges.map((badge) => (
            <span
              key={badge.label}
              className="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/[0.06] px-3 py-1 text-[12.5px] font-medium text-primary"
            >
              {badge.label}
            </span>
          ))}
          {birthCity ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-background/50 px-3 py-1 text-[12.5px] text-muted-foreground">
              {birthCity}
            </span>
          ) : null}
        </div>
      )}
    </section>
  )
}
