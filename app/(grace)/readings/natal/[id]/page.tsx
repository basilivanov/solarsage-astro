
// ############################################################################
// AI_HEADER: MODULE_[ID]_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for page.tsx behavior
// owns:
//   - app/(grace)/readings/natal/[id]/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useCallback, useEffect, useState, use } from "react"
import Link from "next/link"
import { ChevronLeft, ChevronRight, Sparkles, AlertTriangle, RefreshCw } from "lucide-react"
import { motion } from "framer-motion"

import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { fetchNatalReport } from "@/lib/api/natal"
import type {
  NatalReportRead,
  NatalReportSectionRead,
  BackendBlock,
  BackendCalloutTone,
  ProsConsItem,
} from "@/lib/contracts/natal"
import { mapCalloutTone } from "@/lib/contracts/natal"

type Props = {
  params: Promise<{ id: string }>
}

type PageState =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "error"; message: string }
  | { status: "generating"; reportId: string }
  | { status: "failed"; message: string; retryable: boolean; reportId?: string }
  | { status: "ready"; data: NatalReportRead }

export default function NatalReportPage({ params }: Props) {
  const { id } = use(params)
  const [state, setState] = useState<PageState>({ status: "loading" })
  const [activeSection, setActiveSection] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const result = await fetchNatalReport(id)

      if (cancelled) return

      if (!result.ok) {
        if (result.error.type === "not_found") {
          setState({ status: "not_found" })
        } else {
          setState({ status: "error", message: result.error.message })
        }
        return
      }

      const report = result.data

      if (report.status === "READY") {
        setState({ status: "ready", data: report })
        return
      }

      if (report.status === "GENERATING" || report.status === "PENDING") {
        setState({ status: "generating", reportId: report.id })
        return
      }

      if (report.status === "FAILED_RETRYABLE") {
        setState({
          status: "failed",
          message: report.errorMessage || "Generation failed, you can retry",
          retryable: true,
          reportId: report.id,
        })
        return
      }

      if (report.status === "FAILED_PERMANENT") {
        setState({
          status: "failed",
          message: report.errorMessage || "Generation failed permanently",
          retryable: false,
        })
        return
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [id])

  const handleRetry = useCallback(async () => {
    if (state.status !== "failed" || !state.retryable) return
    setState({ status: "loading" })
    // Re-trigger generation with force
    const { fetchNatalGenerate } = await import("@/lib/api/natal")
    const result = await fetchNatalGenerate(true)
    if (!result.ok) {
      setState({ status: "error", message: result.error.message })
      return
    }
    const { reportId, status } = result.data
    if (status === "READY") {
      // Report ready immediately — fetch full content
      const reportResult = await fetchNatalReport(reportId)
      if (reportResult.ok && reportResult.data.status === "READY") {
        setState({ status: "ready", data: reportResult.data })
        return
      }
    }
    if (status === "GENERATING" || status === "PENDING") {
      // Backend is still generating — transition to generating state
      setState({ status: "generating", reportId })
      return
    }
    if (status === "FAILED_RETRYABLE") {
      setState({
        status: "failed",
        message: result.data.errorMessage || "Generation failed, you can retry",
        retryable: true,
        reportId: result.data.reportId,
      })
      return
    }
    if (status === "FAILED_PERMANENT") {
      setState({
        status: "failed",
        message: result.data.errorMessage || "Generation failed permanently",
        retryable: false,
      })
      return
    }
    setState({ status: "error", message: "Unexpected generation status" })
  }, [state])

  // ---- Loading state ----
  if (state.status === "loading") {
    return (
      <div className="flex h-[80dvh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  // ---- Not found ----
  if (state.status === "not_found") {
    return (
      <div className="flex h-[80dvh] flex-col items-center justify-center p-6 text-center space-y-4">
        <h3 className="font-serif text-[20px] font-bold text-foreground">Отчёт не найден</h3>
        <Link href="/readings/natal" className="inline-flex items-center gap-1.5 text-[14px] text-primary">
          <ChevronLeft className="h-4 w-4" />
          Вернуться к превью
        </Link>
      </div>
    )
  }

  // ---- Error ----
  if (state.status === "error") {
    return (
      <div className="flex h-[80dvh] flex-col items-center justify-center p-6 text-center space-y-4">
        <AlertTriangle className="h-8 w-8 text-muted-foreground" />
        <h3 className="font-serif text-[20px] font-bold text-foreground">Ошибка загрузки</h3>
        <p className="text-[14px] text-muted-foreground">{state.message}</p>
        <Link href="/readings/natal" className="inline-flex items-center gap-1.5 text-[14px] text-primary">
          <ChevronLeft className="h-4 w-4" />
          Вернуться к превью
        </Link>
      </div>
    )
  }

  // ---- Still generating ----
  if (state.status === "generating") {
    return (
      <div className="flex h-[80dvh] flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <h3 className="font-serif text-[20px] font-bold text-foreground">Отчёт ещё генерируется</h3>
        <p className="text-[14px] text-muted-foreground">Подождите немного, разбор почти готов</p>
        <Link href={`/readings/natal/generating`} className="inline-flex items-center gap-1.5 text-[14px] text-primary">
          Перейти на экран генерации
        </Link>
      </div>
    )
  }

  // ---- Failed ----
  if (state.status === "failed") {
    return (
      <div className="flex h-[80dvh] flex-col items-center justify-center p-6 text-center space-y-4">
        <AlertTriangle className="h-8 w-8 text-rose-500" />
        <h3 className="font-serif text-[20px] font-bold text-foreground">Не удалось создать разбор</h3>
        <p className="text-[14px] text-muted-foreground">{state.message}</p>
        <div className="flex gap-3">
          {state.retryable && (
            <button
              type="button"
              onClick={handleRetry}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-3 text-[14px] font-medium text-primary-foreground transition active:scale-[0.99]"
            >
              <RefreshCw className="h-4 w-4" />
              Попробовать ещё раз
            </button>
          )}
          <Link href="/readings/natal" className="inline-flex items-center gap-1.5 rounded-xl border border-border/50 bg-card px-4 py-3 text-[14px] font-medium text-foreground">
            <ChevronLeft className="h-4 w-4" />
            Вернуться
          </Link>
        </div>
      </div>
    )
  }

  // ---- Ready: show report ----
  const report = state.data

  // If a section is selected, show it
  if (activeSection) {
    const section = report.sections.find((s) => s.id === activeSection)
    if (section) {
      return (
        <NatalSectionView
          section={section}
          report={report}
          onGoToSection={(id) => setActiveSection(id)}
          onBackToTOC={() => setActiveSection(null)}
        />
      )
    }
  }

  // Show TOC
  const meta = report.meta
  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <Link
          href="/readings/natal"
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Натальная карта</span>
        </Link>
      </header>

      <main className="flex-1 px-5 py-6 max-w-md mx-auto w-full space-y-6">
        {/* Hero */}
        <div className="space-y-2">
          <h1 className="font-serif text-[28px] leading-tight tracking-tight text-foreground">
            Полный разбор карты
          </h1>
          <p className="text-[14px] text-muted-foreground">
            {meta.userName || ""}{meta.userName && meta.birthPlace ? " · " : ""}{meta.birthPlace || ""}{(meta.userName || meta.birthPlace) && meta.birthDate ? " · " : ""}{meta.birthDate?.split("-")[0] || ""}
          </p>
        </div>

        {/* Chapter list */}
        <div className="space-y-2">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Содержание
          </div>
          <div className="space-y-2">
            {report.sections.map((section, index) => (
              <motion.button
                key={section.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 * index, duration: 0.25 }}
                type="button"
                onClick={() => setActiveSection(section.id)}
                className="flex w-full items-start gap-3 rounded-xl border border-border/50 bg-card px-4 py-3.5 text-left transition hover:border-border active:scale-[0.99]"
              >
                <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-primary/10 text-[12px] font-semibold text-primary">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h3 className="text-[14px] font-medium leading-tight text-foreground">
                    {section.title}
                  </h3>
                  {section.summary ? (
                    <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground line-clamp-2">
                      {section.summary}
                    </p>
                  ) : null}
                </div>
                <ChevronRight className="h-4 w-4 flex-none text-muted-foreground/50 mt-1" />
              </motion.button>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}

/* ── Section View ──────────────────────────────────────────────── */

function NatalSectionView({
  section,
  report,
  onGoToSection,
  onBackToTOC,
}: {
  section: NatalReportSectionRead
  report: NatalReportRead
  onGoToSection: (id: string) => void
  onBackToTOC: () => void
}) {
  const sectionIndex = report.sections.findIndex((s) => s.id === section.id)
  const prevSection = sectionIndex > 0 ? report.sections[sectionIndex - 1] : null
  const nextSection = sectionIndex < report.sections.length - 1 ? report.sections[sectionIndex + 1] : null

  return (
    <div className="flex h-full w-full flex-col bg-background overflow-y-auto">
      <header
        className="flex-none px-4 pb-4 border-b border-border/40"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1rem)" }}
      >
        <button
          type="button"
          onClick={onBackToTOC}
          className="inline-flex items-center gap-1.5 text-[14px] text-muted-foreground hover:text-foreground active:scale-95 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Содержание</span>
        </button>
      </header>

      <main className="flex-1 px-5 py-6 max-w-md mx-auto w-full space-y-5">
        {/* Section header */}
        <div className="space-y-1">
          <h1 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
            {section.title}
          </h1>
        </div>

        {/* Blocks */}
        <div className="space-y-4">
          {section.blocks.map((block, index) => (
            <BackendBlockRenderer key={`${section.id}-block-${index}`} block={block} />
          ))}
        </div>

        {/* Next/Prev navigation */}
        <div className="border-t border-border/40 pt-5 space-y-2">
          {nextSection ? (
            <button
              type="button"
              onClick={() => onGoToSection(nextSection.id)}
              className="flex w-full items-center justify-between rounded-xl border border-primary/20 bg-primary/[0.03] px-4 py-3 text-left transition active:scale-[0.99]"
            >
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-[0.1em] text-primary">Следующая</div>
                <div className="text-[13px] font-medium text-foreground">{nextSection.title}</div>
              </div>
              <ChevronRight className="h-4 w-4 flex-none text-primary" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onBackToTOC}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/25 bg-primary/[0.05] px-4 py-3 transition active:scale-[0.99]"
            >
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-[13px] font-medium text-primary">Вернуться к содержанию</span>
            </button>
          )}
          {prevSection ? (
            <button
              type="button"
              onClick={() => onGoToSection(prevSection.id)}
              className="flex w-full items-center gap-2 rounded-xl border border-border/50 bg-card px-4 py-3 text-left transition active:scale-[0.99]"
            >
              <ChevronLeft className="h-4 w-4 flex-none text-muted-foreground" />
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Предыдущая</div>
                <div className="text-[13px] font-medium text-foreground">{prevSection.title}</div>
              </div>
            </button>
          ) : null}
        </div>
      </main>
    </div>
  )
}

/* ── Backend Block Renderer ────────────────────────────────────── */

/**
 * Renders backend-aligned block types.
 * Handles: paragraph, lead, heading, list, callout, pros_cons, quote, divider,
 * highlights, bullets.
 * ProsConsBlock uses ProsConsItem[] ({title, text}), not plain strings.
 * CalloutBlock uses backend tones: info, warning, insight, positive.
 */
function BackendBlockRenderer({ block }: { block: BackendBlock }) {
  switch (block.type) {
    case "lead":
      return (
        <p className="font-serif text-[17px] leading-relaxed text-foreground/90">
          {block.text}
        </p>
      )

    case "paragraph":
      return (
        <p className="text-[14px] leading-relaxed text-foreground/80">
          {block.text}
        </p>
      )

    case "heading":
      return (
        <h2 className={block.level === 2 ? "font-serif text-[20px] font-bold text-foreground" : "font-serif text-[17px] font-semibold text-foreground"}>
          {block.text}
        </h2>
      )

    case "list": {
      const isOrdered = "ordered" in block && block.ordered
      const Tag = isOrdered ? "ol" : "ul"
      return (
        <Tag className={`space-y-1.5 ${isOrdered ? "list-decimal pl-5" : ""}`}>
          {block.items.map((item, i) => (
            <li key={i} className="flex gap-2 text-[14px] leading-relaxed text-foreground/80">
              {!isOrdered && <span className="mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-primary/40" />}
              {item}
            </li>
          ))}
        </Tag>
      )
    }

    case "callout": {
      const displayTone = mapCalloutTone(block.tone as BackendCalloutTone | undefined)
      const toneStyles: Record<string, string> = {
        strength: "border-emerald-500/20 bg-emerald-500/[0.04]",
        risk: "border-rose-500/20 bg-rose-500/[0.04]",
        insight: "border-primary/15 bg-primary/[0.04]",
        neutral: "border-border/50 bg-muted/30",
      }
      const style = toneStyles[displayTone] ?? toneStyles.neutral
      return (
        <aside className={`rounded-xl border px-4 py-3 ${style}`}>
          {block.title ? (
            <div className="text-[12px] font-medium uppercase tracking-[0.1em] text-foreground/70 mb-1">
              {block.title}
            </div>
          ) : null}
          <p className="text-[14px] leading-relaxed text-foreground/85">{block.text}</p>
        </aside>
      )
    }

    case "pros_cons": {
      const pros: ProsConsItem[] = block.pros ?? []
      const cons: ProsConsItem[] = block.cons ?? []
      return (
        <div className="grid grid-cols-2 gap-3">
          {pros.length ? (
            <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/[0.03] px-3.5 py-3">
              <div className="text-[11px] font-medium uppercase tracking-[0.1em] text-emerald-600 dark:text-emerald-400 mb-2">
                {block.prosLabel ?? "Сильные стороны"}
              </div>
              <ul className="space-y-1.5">
                {pros.map((item, i) => (
                  <li key={i} className="text-[13px] leading-relaxed text-foreground/80">
                    {item.title ? <span className="font-medium">{item.title}</span> : null}
                    {item.title && item.text ? " — " : null}
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {cons.length ? (
            <div className="rounded-xl border border-rose-500/15 bg-rose-500/[0.03] px-3.5 py-3">
              <div className="text-[11px] font-medium uppercase tracking-[0.1em] text-rose-600 dark:text-rose-400 mb-2">
                {block.consLabel ?? "Зоны роста"}
              </div>
              <ul className="space-y-1.5">
                {cons.map((item, i) => (
                  <li key={i} className="text-[13px] leading-relaxed text-foreground/80">
                    {item.title ? <span className="font-medium">{item.title}</span> : null}
                    {item.title && item.text ? " — " : null}
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )
    }

    case "quote":
      return (
        <blockquote className="border-l-2 border-primary/30 pl-4 py-1">
          <p className="font-serif text-[15px] leading-relaxed text-foreground/80 italic">
            {block.text}
          </p>
          {block.source ? (
            <cite className="mt-1 block text-[12px] text-muted-foreground not-italic">{block.source}</cite>
          ) : null}
        </blockquote>
      )

    case "divider":
      return <hr className="border-border/30" />

    case "highlights":
      return (
        <div className="space-y-2">
          {block.items.map((item, i) => (
            <div key={i} className="rounded-xl border border-border/50 bg-card px-3.5 py-2.5">
              {item.title ? <div className="text-[12px] font-medium text-foreground/70">{item.title}</div> : null}
              <p className="text-[13px] text-foreground/80">{item.text}</p>
            </div>
          ))}
        </div>
      )

    case "bullets":
      return (
        <ul className="space-y-1.5">
          {block.items.map((item, i) => (
            <li key={i} className="flex gap-2 text-[14px] leading-relaxed text-foreground/80">
              <span className="mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-primary/40" />
              {item}
            </li>
          ))}
        </ul>
      )

    default:
      // Graceful skip for unknown block types
      return null
  }
}
