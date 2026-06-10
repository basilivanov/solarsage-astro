"use client"

import { useCallback, useEffect, useState, use } from "react"
import Link from "next/link"
import { ChevronLeft, ChevronRight, Sparkles } from "lucide-react"
import { motion } from "framer-motion"

import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { MOCK_NATAL_REPORT } from "@/lib/mocks/natal"
import type { NatalReport, ReportSection } from "@/lib/contracts/natal"

type Props = {
  params: Promise<{ id: string }>
}

export default function NatalReportPage({ params }: Props) {
  const { id } = use(params)
  const [report, setReport] = useState<NatalReport | null>(null)
  const [activeSection, setActiveSection] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // TODO: Replace with real API call when backend is ready
    // GET /api/natal/report/{id}
    if (IS_DEMO_MODE || id === "demo") {
      setReport(MOCK_NATAL_REPORT)
      setLoading(false)
      return
    }

    // For now, always use mock
    setReport(MOCK_NATAL_REPORT)
    setLoading(false)
  }, [id])

  const handleSectionClick = useCallback((sectionId: string) => {
    setActiveSection(sectionId)
  }, [])

  if (loading) {
    return (
      <div className="flex h-[80dvh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!report) {
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
            {report.meta.name} · {report.meta.birth.place} · {report.meta.birth.date.split("-")[0]}
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
                onClick={() => handleSectionClick(section.id)}
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
  section: ReportSection
  report: NatalReport
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
          {section.eyebrow ? (
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-primary">
              {section.eyebrow}
            </span>
          ) : null}
          <h1 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
            {section.title}
          </h1>
        </div>

        {/* Blocks */}
        <div className="space-y-4">
          {section.blocks.map((block, index) => (
            <NatalBlock key={`${section.id}-block-${index}`} block={block} />
          ))}
        </div>

        {/* Prev/Next navigation */}
        <div className="border-t border-border/40 pt-5 space-y-2">
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
        </div>
      </main>
    </div>
  )
}

/* ── Block Renderer ────────────────────────────────────────────── */

function NatalBlock({ block }: { block: any }) {
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

    case "list":
      return (
        <ul className="space-y-1.5">
          {block.items?.map((item: string, i: number) => (
            <li key={i} className="flex gap-2 text-[14px] leading-relaxed text-foreground/80">
              <span className="mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-primary/40" />
              {item}
            </li>
          ))}
        </ul>
      )

    case "callout": {
      const toneStyles: Record<string, string> = {
        strength: "border-emerald-500/20 bg-emerald-500/[0.04]",
        risk: "border-rose-500/20 bg-rose-500/[0.04]",
        insight: "border-primary/15 bg-primary/[0.04]",
        neutral: "border-border/50 bg-muted/30",
      }
      const style = toneStyles[block.tone ?? "neutral"] ?? toneStyles.neutral
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

    case "pros_cons":
      return (
        <div className="grid grid-cols-2 gap-3">
          {block.pros?.length ? (
            <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/[0.03] px-3.5 py-3">
              <div className="text-[11px] font-medium uppercase tracking-[0.1em] text-emerald-600 dark:text-emerald-400 mb-2">
                {block.prosLabel ?? "За"}
              </div>
              <ul className="space-y-1.5">
                {block.pros.map((item: string, i: number) => (
                  <li key={i} className="text-[13px] leading-relaxed text-foreground/80">{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {block.cons?.length ? (
            <div className="rounded-xl border border-rose-500/15 bg-rose-500/[0.03] px-3.5 py-3">
              <div className="text-[11px] font-medium uppercase tracking-[0.1em] text-rose-600 dark:text-rose-400 mb-2">
                {block.consLabel ?? "Против"}
              </div>
              <ul className="space-y-1.5">
                {block.cons.map((item: string, i: number) => (
                  <li key={i} className="text-[13px] leading-relaxed text-foreground/80">{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )

    case "quote":
      return (
        <blockquote className="border-l-2 border-primary/30 pl-4 py-1">
          <p className="font-serif text-[15px] leading-relaxed text-foreground/80 italic">
            {block.text}
          </p>
          {block.cite ? (
            <cite className="mt-1 block text-[12px] text-muted-foreground not-italic">{block.cite}</cite>
          ) : null}
        </blockquote>
      )

    case "divider":
      return <hr className="border-border/30" />

    default:
      return null
  }
}
