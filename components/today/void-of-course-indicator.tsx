"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { AlertCircle, CheckCircle2, Clock, ChevronDown } from "lucide-react"
import { getVoidOfCourse } from "@/lib/moon"

/**
 * VoidOfCourseIndicator — shows whether the Moon is currently
 * "void of course" (без курса) and when the next VoC period is.
 *
 * In traditional astrology, the VoC Moon is a time to avoid starting
 * new ventures. This widget gives a clear at-a-glance status plus
 * an expandable detail with timing.
 */

interface VoidOfCourseIndicatorProps {
  date: Date
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
}

function formatDateShort(d: Date): string {
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
  return `${d.getDate()} ${months[d.getMonth()]}`
}

export function VoidOfCourseIndicator({ date }: VoidOfCourseIndicatorProps) {
  const [expanded, setExpanded] = useState(false)

  const voc = useMemo(() => getVoidOfCourse(date), [date])

  // Find next VoC: scan forward up to 7 days
  const nextVoc = useMemo(() => {
    if (voc.isVoid) return null
    for (let h = 1; h <= 168; h++) {
      const test = new Date(date.getTime() + h * 3600000)
      const v = getVoidOfCourse(test)
      if (v.isVoid) {
        return { startsAt: test, durationHours: v.durationHours ?? 0, endsAt: v.endsAt }
      }
    }
    return null
  }, [date, voc.isVoid])

  return (
    <section className="px-6" aria-label="Луна без курса">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="group relative w-full overflow-hidden rounded-2xl border p-3.5 text-left transition-all active:scale-[0.99]"
        style={{
          borderColor: voc.isVoid ? "oklch(0.65 0.15 60 / 0.35)" : "oklch(0.5 0.03 295 / 0.2)",
          background: voc.isVoid
            ? "linear-gradient(135deg, oklch(0.65 0.12 60 / 0.06), oklch(0.60 0.06 295 / 0.04))"
            : "linear-gradient(135deg, oklch(0.65 0.13 145 / 0.04), oklch(0.60 0.06 295 / 0.03))",
        }}
        aria-expanded={expanded}
      >
        <div className="relative flex items-center gap-3">
          {/* Status icon */}
          <div
            className="flex h-9 w-9 flex-none items-center justify-center rounded-full"
            style={{
              background: voc.isVoid
                ? "oklch(0.65 0.15 60 / 0.15)"
                : "oklch(0.65 0.13 145 / 0.12)",
            }}
          >
            {voc.isVoid ? (
              <AlertCircle className="h-4 w-4" strokeWidth={2} style={{ color: "oklch(0.60 0.15 60)" }} />
            ) : (
              <CheckCircle2 className="h-4 w-4" strokeWidth={2} style={{ color: "oklch(0.60 0.13 145)" }} />
            )}
          </div>

          {/* Status text */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span
                className="text-[13px] font-medium"
                style={{ color: voc.isVoid ? "oklch(0.55 0.15 60)" : "oklch(0.50 0.13 145)" }}
              >
                {voc.note}
              </span>
              {voc.isVoid && voc.durationHours != null && (
                <span className="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-medium tabular-nums text-amber-700 dark:text-amber-400">
                  {voc.durationHours}ч
                </span>
              )}
            </div>
            <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
              {voc.isVoid
                ? `До ${voc.endsAt ? formatTime(voc.endsAt) : "—"}`
                : nextVoc
                  ? `След. без курса ${formatDateShort(nextVoc.startsAt)} в ${formatTime(nextVoc.startsAt)}`
                  : "Ближайшие 7 дней без курса нет"}
            </p>
          </div>

          <ChevronDown
            className={`h-4 w-4 flex-none text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`}
            strokeWidth={1.8}
          />
        </div>

        {/* Expandable detail */}
        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="mt-3 space-y-2 border-t border-border/40 pt-3">
                <p className="text-[12px] leading-relaxed text-foreground/80">
                  {voc.recommendation}
                </p>
                {voc.isVoid && (
                  <div className="flex items-center gap-2 rounded-lg bg-secondary/40 px-3 py-2 text-[11px]">
                    <Clock className="h-3 w-3 text-muted-foreground" strokeWidth={1.8} />
                    <span className="text-muted-foreground">Период:</span>
                    <span className="tabular-nums text-foreground">
                      {voc.startedAt ? formatTime(voc.startedAt) : "—"} — {voc.endsAt ? formatTime(voc.endsAt) : "—"}
                    </span>
                  </div>
                )}
                <p className="text-[10px] leading-relaxed text-muted-foreground/60">
                  Луна «без курса» — когда она не делает больше главных аспектов до перехода в следующий знак. Традиционно время отдыха, а не начинаний.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </button>
    </section>
  )
}
