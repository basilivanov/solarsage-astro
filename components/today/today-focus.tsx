// ############################################################################
// AI_HEADER: MODULE_TODAY_FOCUS_CARD
// ROLE: Human-first TodayFocus card component for "What converged today" and "Events of the day".
// DEPENDENCIES: react, lucide-react, lib/contracts/today, lib/icons, lib/presentation/today-v2
// GRACE_ANCHORS: [TODAY_FOCUS_CARD]
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-FOCUS-CARD
// purpose: Render TodayFocus block according to 22_TZ design contract and delegate sphere selection to parent.
// owns:
//   - components/today/today-focus.tsx
// inputs: focus (TodayFocus | null | undefined), onSphereSelect (function), onRetry (function optional)
// outputs: section with data-testid="today-focus"
// dependencies: lib/contracts/today, lib/icons, lib/presentation/today-v2
// side_effects: calls onSphereSelect/onRetry callbacks on user activation
// emitted_logs: none
// failure_policy: renders fallback unavailable state when focus is invalid
// END_MODULE_CONTRACT: M-TODAY-FOCUS-CARD

// START_MODULE_MAP: M-TODAY-FOCUS-CARD
// public_entrypoints:
//   - TodayFocusCard
// semantic_blocks:
//   - TODAY_FOCUS_CARD: main focus card container with events, featured spheres, and technical disclosure
// owned_tests:
//   - __tests__/components/TodayFocus.test.tsx
// END_MODULE_MAP: M-TODAY-FOCUS-CARD

"use client"

import React, { useState } from "react"
import { ChevronDown, ChevronRight, Sparkles, RefreshCw } from "lucide-react"
import type { TodayFocus, TodayFocusEvent } from "@/lib/contracts/today"
import { getIcon, type IconName } from "@/lib/icons"
import { getHumanSphereLabel } from "@/lib/presentation/today-v2"
import { CANONICAL_PRODUCT_ORDER } from "@/lib/display/sphere-labels"

const SPHERE_ICON_BY_KEY: Record<string, IconName> = Object.fromEntries(
  CANONICAL_PRODUCT_ORDER.map((item) => [item.key, item.iconName as IconName]),
)

interface TodayFocusCardProps {
  focus?: TodayFocus | null
  onSphereSelect: (key: string) => void
  onRetry?: () => void
}

function formatLocalTime(occursAt: string | Date | null | undefined, timezoneName: string): string {
  if (!occursAt) return ""
  try {
    const dt = typeof occursAt === "string" ? new Date(occursAt) : occursAt
    return dt.toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: timezoneName || "UTC",
    })
  } catch {
    return ""
  }
}

function formatKindLabel(kind: string): { label: string; colorClass: string } {
  switch (kind) {
    case "exact":
    case "peak":
      return { label: "точный пик", colorClass: "text-violet-700 dark:text-violet-300" }
    case "starts":
      return { label: "начинается", colorClass: "text-amber-700 dark:text-amber-300" }
    case "building":
      return { label: "пик завтра", colorClass: "text-amber-700 dark:text-amber-300" }
    case "separating":
      return { label: "ослабевает", colorClass: "text-slate-500 dark:text-slate-400" }
    default:
      return { label: "событие", colorClass: "text-violet-700 dark:text-violet-300" }
  }
}

// START_BLOCK: TODAY_FOCUS_CARD
export function TodayFocusCard({ focus, onSphereSelect, onRetry }: TodayFocusCardProps) {
  const [techOpen, setTechOpen] = useState(false)

  if (!focus) {
    return (
      <section
        data-testid="today-focus"
        data-state="unavailable"
        data-content-state="unavailable"
        className="px-5"
      >
        <div className="flex items-center justify-between text-[13px] text-muted-foreground">
          <span>Не удалось рассчитать акценты дня. Попробуй обновить позже.</span>
          {onRetry && (
            <button
              type="button"
              data-testid="today-focus-retry"
              onClick={onRetry}
              className="ml-2 flex items-center gap-1 font-medium text-violet-700 dark:text-violet-300 hover:underline cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Обновить
            </button>
          )}
        </div>
      </section>
    )
  }

  const { state, convergence, events = [], featuredSpheres = [], contentState = "not_needed" } = focus

  if (state === "unavailable") {
    return (
      <section
        data-testid="today-focus"
        data-state="unavailable"
        data-content-state={contentState}
        className="px-5"
      >
        <div className="flex items-center justify-between text-[13px] text-muted-foreground">
          <span>Не удалось рассчитать акценты дня. Попробуй обновить позже.</span>
          {onRetry && (
            <button
              type="button"
              data-testid="today-focus-retry"
              onClick={onRetry}
              className="ml-2 flex items-center gap-1 font-medium text-violet-700 dark:text-violet-300 hover:underline cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Обновить
            </button>
          )}
        </div>
      </section>
    )
  }

  if (state === "background_only") {
    return (
      <section
        data-testid="today-focus"
        data-state="background_only"
        data-content-state={contentState}
        className="px-5 text-[13px] leading-relaxed text-muted-foreground"
      >
        <span>Фон периода: активны длительные астрологические факторы года.</span>
      </section>
    )
  }

  if (state === "no_accent") {
    return (
      <section
        data-testid="today-focus"
        data-state="no_accent"
        data-content-state={contentState}
        className="px-5 text-[13px] text-muted-foreground/80"
      >
        <span>Сегодня нет выраженного схождения нескольких факторов.</span>
      </section>
    )
  }

  const isConvergence = state === "convergence_today"
  const eyebrowText = isConvergence ? "СОШЛОСЬ СЕГОДНЯ" : "СОБЫТИЯ ДНЯ"
  const factorCount = convergence?.independentFactorCount ?? 0
  const factorCountStr = factorCount < 10 ? `0${factorCount}` : `${factorCount}`
  const actionText = featuredSpheres[0]?.action?.trim() || null

  return (
    <section
      data-testid="today-focus"
      data-state={state}
      data-content-state={contentState}
      className="px-5"
    >
      <div className="relative overflow-hidden rounded-[24px] border border-border/60 bg-card p-5 shadow-[0_18px_48px_-28px_rgba(76,29,149,0.35)] dark:border-violet-400/25">
        {/* Header eyebrow */}
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-300">
            {eyebrowText}
          </span>
          {isConvergence && factorCount > 0 && (
            <span className="text-[11px] font-semibold text-muted-foreground tabular-nums">
              {factorCountStr} ▸
            </span>
          )}
        </div>

        {/* Title & Summary for convergence */}
        {isConvergence && (
          <div className="mt-2 space-y-1.5">
            <h3 className="font-serif text-[22px] leading-tight text-foreground font-semibold">
              {convergence?.title || "Что сошлось именно сегодня"}
            </h3>
            {contentState === "pending" ? (
              <div className="space-y-1 py-1" role="status" aria-busy="true">
                <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
                <span className="sr-only">Разбор пишется…</span>
              </div>
            ) : contentState === "unavailable" ? (
              <p className="text-[13.5px] leading-relaxed text-muted-foreground italic">
                Персональный разбор пока не готов
              </p>
            ) : convergence?.summary ? (
              <p className="text-[15px] leading-relaxed text-foreground/85">
                {convergence.summary}
              </p>
            ) : null}
          </div>
        )}

        {/* Divider */}
        {(isConvergence || events.length > 0) && (
          <div className="my-3.5 border-t border-border/40" aria-hidden="true" />
        )}

        {/* Events List (0..3) */}
        {events.length > 0 && (
          <div className="space-y-3.5">
            {events.map((ev: TodayFocusEvent) => {
              const timeStr = formatLocalTime(ev.occursAt, ev.timezone)
              const timeDisplay =
                timeStr ||
                (ev.precision === "date" || ev.precision === "window" ? "весь день" : "днём")
              const kindMeta = formatKindLabel(ev.kind)
              const isTomorrow = ev.kind === "building"

              return (
                <div
                  key={ev.id}
                  data-testid="today-focus-event"
                  data-event-kind={ev.kind}
                  className={`flex items-start gap-3.5 ${isTomorrow ? "opacity-60" : ""}`}
                >
                  <span className="w-12 flex-none font-mono text-[15px] font-semibold tabular-nums text-foreground pt-0.5">
                    {timeDisplay}
                  </span>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-x-1.5 text-[15px] font-semibold leading-snug text-foreground">
                      <span>{ev.humanTitle}</span>
                      <span className="text-muted-foreground/60 font-normal">·</span>
                      <span className={`text-[12px] font-medium ${kindMeta.colorClass}`}>
                        {kindMeta.label}
                      </span>
                    </div>

                    {contentState === "pending" ? (
                      <div className="space-y-1 py-0.5" role="status" aria-busy="true">
                        <div className="h-3.5 w-4/5 rounded bg-muted animate-pulse" />
                        <span className="sr-only">Разбор пишется…</span>
                      </div>
                    ) : ev.meaning ? (
                      <p className="text-[13.5px] leading-relaxed text-muted-foreground">
                        {ev.meaning}
                      </p>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Featured Spheres (0..3) */}
        {isConvergence && featuredSpheres.length > 0 && (
          <div className="mt-4 pt-3 border-t border-border/40">
            <p className="text-[12px] font-semibold text-muted-foreground mb-2">
              Где проявится:
            </p>
            <div className="space-y-2">
              {featuredSpheres.map((sphere) => {
                const Icon = getIcon(SPHERE_ICON_BY_KEY[sphere.key] ?? "orbit")
                const label = getHumanSphereLabel({ key: sphere.key, label: sphere.key })

                return (
                  <button
                    key={sphere.key}
                    type="button"
                    data-testid="today-featured-sphere"
                    data-sphere-key={sphere.key}
                    aria-haspopup="dialog"
                    onClick={() => onSphereSelect(sphere.key)}
                    className="flex min-h-[52px] w-full items-center gap-3 rounded-2xl border border-border/60 bg-card px-3.5 text-left text-foreground transition hover:border-violet-300 hover:bg-violet-50/40 dark:hover:bg-violet-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 cursor-pointer active:scale-[0.985]"
                  >
                    <span className="flex h-8 w-8 flex-none items-center justify-center rounded-xl bg-violet-100/80 text-violet-700 dark:bg-violet-500/20 dark:text-violet-100">
                      <Icon className="h-4 w-4" strokeWidth={1.8} aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1 text-[14.5px] font-medium leading-snug">
                      {label}
                    </span>
                    <ChevronRight className="h-4 w-4 flex-none text-muted-foreground" aria-hidden="true" />
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Single Action Pill */}
        {isConvergence && actionText && contentState === "ready" && (
          <div className="mt-3.5 flex items-start gap-2.5 rounded-2xl border border-violet-200/70 bg-violet-50/55 px-3.5 py-2.5 text-[14px] font-medium text-foreground dark:border-violet-400/20 dark:bg-violet-500/10">
            <Sparkles className="h-4 w-4 text-violet-700 dark:text-violet-300 flex-none mt-0.5" aria-hidden="true" />
            <span className="min-w-0 flex-1 leading-snug">{actionText}</span>
          </div>
        )}

        {/* Technical Disclosure */}
        <div className="mt-4 pt-3 border-t border-border/40">
          <button
            type="button"
            data-testid="today-focus-technical-toggle"
            aria-expanded={techOpen}
            aria-controls="today-focus-technical-content"
            onClick={() => setTechOpen((prev) => !prev)}
            className="flex items-center justify-between w-full text-[12.5px] font-medium text-muted-foreground hover:text-foreground transition cursor-pointer"
          >
            <span>Как это рассчитано</span>
            <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${techOpen ? "rotate-180" : ""}`} aria-hidden="true" />
          </button>

          {techOpen && (
            <div
              id="today-focus-technical-content"
              data-testid="today-focus-technical-content"
              className="mt-2 space-y-1.5 text-[12px] text-muted-foreground/90 bg-muted/30 p-3 rounded-xl"
            >
              <p><strong className="font-semibold">Состояние:</strong> {state}</p>
              {events.map((ev) => (
                <p key={ev.id}>
                  <strong className="font-semibold">{ev.technicalTitle || ev.humanTitle}:</strong> {ev.kind} ({ev.timezone})
                </p>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
// END_BLOCK: TODAY_FOCUS_CARD
