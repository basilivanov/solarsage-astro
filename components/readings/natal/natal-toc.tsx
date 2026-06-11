
// ############################################################################
// AI_HEADER: MODULE_NATAL_NATAL_TOC
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal/natal-toc.tsx
// owns:
//   - components/readings/natal/natal-toc.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import Link from "next/link"
import { ArrowLeft, ArrowRight, BookOpen, Calendar, MapPin } from "lucide-react"

import type { NatalReport } from "@/lib/contracts/natal"
import { HighlightsStrip } from "./highlights-strip"
import { SpheresWidget } from "./widgets/spheres-widget"

type Props = {
  report: NatalReport
}

/**
 * Оглавление натальной карты — главный экран /readings/natal.
 *
 * Структура mobile-first:
 *   1. Compact-хедер с back-кнопкой к списку разборов;
 *   2. Hero: имя, мета (дата / место), highlights;
 *   3. Top-сферы (виджет, ограниченный сверху);
 *   4. Список глав — переходы на /readings/natal/[id].
 *
 * Не один длинный скролл — каждая глава открывается отдельной страницей,
 * это даёт нативный back и нормальное scroll-restoration в Telegram.
 */
export function NatalToc({ report }: Props) {
  const { meta, highlights = [], spheres = [], sections } = report

  return (
    <div className="flex h-full w-full flex-col">
      {/* Sticky compact-хедер с back-нав */}
      <header
        className="sticky top-0 z-10 flex flex-none items-center gap-2 border-b border-border/60 bg-background/85 px-3 py-3 backdrop-blur-md"
        style={{ paddingTop: "max(env(safe-area-inset-top), 0.75rem)" }}
      >
        <Link
          href="/readings"
          aria-label="Назад к разборам"
          className="flex h-9 w-9 items-center justify-center rounded-full text-foreground/70 transition active:scale-95 active:bg-muted/60"
        >
          <ArrowLeft className="h-4 w-4" strokeWidth={1.75} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Разбор
          </div>
          <div className="truncate text-[14px] font-medium text-foreground">
            Натальная карта
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto pb-10">
        {/* Hero */}
        <section className="px-5 pt-5">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Глубокий разбор
          </div>
          <h1 className="mt-1 font-serif text-[30px] leading-[1.1] tracking-tight text-foreground">
            {meta.name}
            <span className="ml-2 text-foreground/50">·</span>{" "}
            <span className="text-foreground/65">натал</span>
          </h1>

          <ul className="mt-3 flex flex-col gap-1 text-[13px] leading-snug text-muted-foreground">
            <li className="flex items-center gap-2">
              <Calendar
                className="h-3.5 w-3.5 flex-none text-muted-foreground/70"
                strokeWidth={1.7}
              />
              <span>
                {formatBirth(meta.birth.date, meta.birth.time)}
                {meta.birth.timezone ? (
                  <span className="text-muted-foreground/60">
                    {" "}
                    · {meta.birth.timezone}
                  </span>
                ) : null}
              </span>
            </li>
            {meta.birth.place ? (
              <li className="flex items-center gap-2">
                <MapPin
                  className="h-3.5 w-3.5 flex-none text-muted-foreground/70"
                  strokeWidth={1.7}
                />
                <span>{meta.birth.place}</span>
              </li>
            ) : null}
            {meta.houseSystem ? (
              <li className="flex items-center gap-2">
                <BookOpen
                  className="h-3.5 w-3.5 flex-none text-muted-foreground/70"
                  strokeWidth={1.7}
                />
                <span>Система домов: {meta.houseSystem}</span>
              </li>
            ) : null}
          </ul>
        </section>

        {/* Highlights */}
        {highlights.length > 0 ? (
          <section className="mt-6 px-5" aria-labelledby="natal-highlights">
            <h2
              id="natal-highlights"
              className="sr-only"
            >
              Ключевые акценты
            </h2>
            <HighlightsStrip items={highlights} />
          </section>
        ) : null}

        {/* Top-сферы */}
        {spheres.length > 0 ? (
          <section className="mt-7 px-5" aria-labelledby="natal-top-spheres">
            <div className="mb-3 flex items-baseline justify-between">
              <h2
                id="natal-top-spheres"
                className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground"
              >
                Главные доминанты
              </h2>
              <span className="text-[11px] text-muted-foreground/70">
                top {Math.min(5, spheres.length)}
              </span>
            </div>
            <SpheresWidget spheres={spheres} limit={5} title="" />
          </section>
        ) : null}

        {/* Главы */}
        <section
          className="mt-8 px-5"
          aria-labelledby="natal-chapters"
        >
          <div className="mb-3 flex items-baseline justify-between">
            <h2
              id="natal-chapters"
              className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground"
            >
              Главы разбора
            </h2>
            <span className="text-[11px] text-muted-foreground/70">
              {sections.length}
            </span>
          </div>

          <ol className="overflow-hidden rounded-2xl border border-border/70 bg-card">
            {sections.map((s, i) => (
              <li key={s.id}>
                <Link
                  href={`/readings/natal/${s.id}`}
                  prefetch
                  className={`group flex items-start gap-4 px-4 py-4 transition active:bg-muted/40 ${
                    i < sections.length - 1
                      ? "border-b border-border/60"
                      : ""
                  }`}
                >
                  <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-secondary/60 font-mono text-[12px] tabular-nums text-foreground/70">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                      {s.eyebrow ?? `Глава ${i + 1}`}
                    </div>
                    <h3 className="mt-0.5 font-serif text-[17px] leading-tight tracking-tight text-foreground">
                      {s.title}
                    </h3>
                    {s.summary ? (
                      <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                        {s.summary}
                      </p>
                    ) : null}
                  </div>
                  <ArrowRight
                    className="mt-2 h-4 w-4 flex-none text-muted-foreground/60 transition-transform group-active:translate-x-0.5"
                    strokeWidth={1.7}
                  />
                </Link>
              </li>
            ))}
          </ol>
        </section>

        {meta.generatedAt ? (
          <p className="mt-8 px-5 text-center text-[11.5px] leading-relaxed text-muted-foreground/70">
            Сформировано {formatGeneratedAt(meta.generatedAt)}
          </p>
        ) : null}
      </div>
    </div>
  )
}

function formatBirth(date: string, time?: string) {
  // Ожидаем YYYY-MM-DD; парсим вручную, чтобы не зависеть от локали браузера
  const [y, m, d] = date.split("-").map(Number)
  const months = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
  ]
  const monthName = months[(m ?? 1) - 1] ?? ""
  const datePart = `${d} ${monthName} ${y}`
  return time ? `${datePart}, ${time}` : datePart
}

function formatGeneratedAt(iso: string) {
  try {
    const d = new Date(iso)
    return d.toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
    })
  } catch {
    return iso
  }
}
