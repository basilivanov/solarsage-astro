// ############################################################################
// AI_HEADER: MODULE_TODAY_WHY_EXPANDED
// ROLE: UI component — Renders why sections or W6 whyToday block.
// ############################################################################
"use client"

import { useState } from "react"
import { useSearchParams } from "next/navigation"
import { ChevronUp } from "lucide-react"

import { getIcon } from "@/lib/icons"
import type { TodayWhySection, TodayV2WhyTodayItem } from "@/lib/contracts/today"
import { TechniqueChip } from "./technique-chip"

type Props = {
  sections: TodayWhySection[]
  keyInsight: string
  whyToday?: TodayV2WhyTodayItem[] | null
}

export function WhyExpanded({ sections, keyInsight, whyToday }: Props) {
  const searchParams = useSearchParams()
  // Deeplink `?why=1` автоматически разворачивает блок
  const defaultOpen = searchParams?.get("why") === "1"
  const [open, setOpen] = useState(defaultOpen)

  const hasV2 = whyToday && whyToday.length > 0
  const showWhyBlock = hasV2 || sections.length > 0
  if (!showWhyBlock) return null

  return (
    <section className="px-5" aria-label="Почему так у меня" data-testid="why-expanded">
      <div className="overflow-hidden rounded-2xl border border-border/70 bg-card">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
        >
          <div className="min-w-0">
            <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Глубже
            </div>
            <div className="mt-0.5 font-serif text-[22px] leading-tight text-foreground">
              {hasV2 ? "Почему именно сегодня" : "Почему так у меня"}
            </div>
          </div>
          <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-accent text-accent-foreground">
            <ChevronUp
              className={`h-4 w-4 transition-transform ${open ? "" : "rotate-180"}`}
              strokeWidth={1.75}
            />
          </div>
        </button>

        {open && (
          <div className="border-t border-border/60 bg-secondary/40 px-5 pb-6 pt-5">
            <p className="mb-5 font-serif text-[16px] italic leading-relaxed text-muted-foreground">
              {hasV2
                ? "Здесь видно, почему сегодняшний сюжет относится именно к вашей карте и какие независимые циклы его подтверждают."
                : "Как именно сегодняшние транзиты ложатся на твою натальную карту и почему день звучит так, а не иначе."}
            </p>

            {hasV2 ? (
              <div data-testid="why-today" className="space-y-5">
                {whyToday!.map((item, i) => (
                  <div key={item.id || i} className="grid grid-cols-[auto_1fr] gap-3.5">
                    <div className="flex flex-col items-center">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border/70 bg-card text-primary font-bold text-xs">
                        {String(i + 1).padStart(2, "0")}
                      </div>
                      {i !== whyToday!.length - 1 && (
                        <span className="mt-1 w-px flex-1 bg-border/70" />
                      )}
                    </div>
                    <div className="pb-1">
                      <h3 className="text-[15px] font-semibold leading-snug text-foreground">
                        {item.title}
                      </h3>
                      <p className="mt-1.5 font-serif text-[16px] leading-[1.55] text-foreground/85">
                        {item.body}
                      </p>
                      {item.techniques && item.techniques.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.techniques.map((tech) => (
                            <TechniqueChip key={tech} technique={tech} />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <ol className="space-y-5">
                {sections.map((s, i) => {
                  const Icon = getIcon(s.iconName)
                  return (
                    <li key={s.id} className="grid grid-cols-[auto_1fr] gap-3.5">
                      <div className="flex flex-col items-center">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border/70 bg-card text-primary">
                          <Icon className="h-4 w-4" strokeWidth={1.6} />
                        </div>
                        {i !== sections.length - 1 && (
                          <span className="mt-1 w-px flex-1 bg-border/70" />
                        )}
                      </div>
                      <div className="pb-1">
                        <div className="flex items-baseline gap-2">
                          <span className="text-[10px] font-medium tracking-[0.14em] text-muted-foreground">
                            {String(i + 1).padStart(2, "0")}
                          </span>
                          <h3 className="text-[15px] font-semibold leading-snug text-foreground">
                            {s.title}
                          </h3>
                        </div>

                        {s.paragraphs.map((p, idx) => (
                          <p
                            key={idx}
                            className="mt-1.5 font-serif text-[16px] leading-[1.55] text-foreground/85"
                          >
                            {p}
                          </p>
                        ))}

                        {s.bullets && s.bullets.length > 0 ? (
                          <ul className="mt-2.5 space-y-1.5">
                            {s.bullets.map((b, idx) => (
                              <li
                                key={idx}
                                className="flex items-start gap-2 font-serif text-[16px] leading-[1.55] text-foreground/75"
                              >
                                <span
                                  aria-hidden
                                  className="mt-[7px] h-1 w-1 flex-none rounded-full bg-foreground/40"
                                />
                                <span>{b}</span>
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    </li>
                  )
                })}
              </ol>
            )}

            {!hasV2 && (
              <div className="mt-6 rounded-xl border border-border/70 bg-card px-4 py-3.5">
                <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                  Ключ дня
                </div>
                <div className="mt-1 font-serif text-[17px] leading-snug text-foreground">
                  {keyInsight}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
