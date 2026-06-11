
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_BLOCK_RENDERER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/horary/horary-block-renderer.tsx
// owns:
//   - components/readings/horary/horary-block-renderer.tsx
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

"use client"

import { Check, Sparkles, AlertTriangle, Info, Quote, CheckCircle2, XCircle, HelpCircle, Timer, AlertOctagon } from "lucide-react"
import type { HoraryBlock } from "@/lib/contracts/horary"
import type { CalloutTone } from "@/lib/contracts/natal"

type Props = {
  block: HoraryBlock
}

const CONFIDENCE_LABELS: Record<"low" | "medium" | "high", string> = {
  low: "Низкая",
  medium: "Средняя",
  high: "Высокая",
}

const CONFIDENCE_INTRO: Record<"low" | "medium" | "high", string> = {
  low: "Уверенность разбора:",
  medium: "Уверенность разбора:",
  high: "Уверенность разбора:",
}

export function HoraryBlockRenderer({ block }: Props) {
  switch (block.type) {
    case "paragraph":
      return (
        <p className="font-serif text-[17px] leading-[1.55] text-foreground/85">
          {block.text}
        </p>
      )

    case "lead":
      return (
        <p className="font-serif text-[19px] leading-[1.5] text-foreground">
          {block.text}
        </p>
      )

    case "heading": {
      const sizes =
        block.level === 2
          ? "font-serif text-[20px] leading-tight tracking-tight text-foreground"
          : "font-serif text-[16px] leading-tight tracking-tight text-foreground/90"
      return <h2 className={sizes}>{block.text}</h2>
    }

    case "list": {
      const isCheck = block.style === "check"
      return (
        <ul className="flex flex-col gap-2">
          {block.items.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-2.5 text-[14.5px] leading-relaxed text-foreground/80"
            >
              {isCheck ? (
                <Check
                  className="mt-1 h-3.5 w-3.5 flex-none text-primary"
                  strokeWidth={2}
                />
              ) : (
                <span
                  aria-hidden
                  className="mt-[10px] h-1 w-1 flex-none rounded-full bg-foreground/40"
                />
              )}
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )
    }

    case "callout": {
      const tone = block.tone ?? "neutral"
      const styles = calloutStyles(tone as any)
      const Icon = styles.icon
      return (
        <aside
          className={`flex gap-3 rounded-2xl border px-4 py-3.5 ${styles.wrap}`}
        >
          <div
            className={`mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-full ${styles.iconWrap}`}
          >
            <Icon className="h-4 w-4" strokeWidth={1.7} />
          </div>
          <div className="min-w-0 flex-1">
            {block.title ? (
              <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {block.title}
              </div>
            ) : null}
            <p
              className={`font-serif text-[15.5px] leading-[1.5] ${
                block.title ? "mt-1" : ""
              } ${styles.text}`}
            >
              {block.text}
            </p>
          </div>
        </aside>
      )
    }

    case "pros_cons":
      return (
        <div className="grid gap-2.5">
          {block.pros && block.pros.length > 0 ? (
            <div className="rounded-2xl border border-border/70 bg-card px-4 py-3.5">
              <div className="mb-2 text-[10.5px] font-medium uppercase tracking-[0.14em] text-primary">
                {block.prosLabel ?? "Сила"}
              </div>
              <ul className="flex flex-col gap-1.5">
                {block.pros.map((p, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-[14px] leading-relaxed text-foreground/85"
                  >
                    <Check
                      className="mt-1 h-3.5 w-3.5 flex-none text-primary"
                      strokeWidth={2}
                    />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {block.cons && block.cons.length > 0 ? (
            <div className="rounded-2xl border border-border/70 bg-muted/40 px-4 py-3.5">
              <div className="mb-2 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {block.consLabel ?? "Риск"}
              </div>
              <ul className="flex flex-col gap-1.5">
                {block.cons.map((c, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-[14px] leading-relaxed text-foreground/75"
                  >
                    <AlertTriangle
                      className="mt-1 h-3.5 w-3.5 flex-none text-foreground/50"
                      strokeWidth={1.7}
                    />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )

    case "quote":
      return (
        <figure className="rounded-2xl border border-border/70 bg-secondary/40 px-5 py-4">
          <Quote
            aria-hidden
            className="mb-2 h-4 w-4 text-primary/60"
            strokeWidth={1.6}
          />
          <blockquote className="font-serif text-[17px] italic leading-[1.5] text-foreground/85">
            {block.text}
          </blockquote>
          {block.source ? (
            <figcaption className="mt-2 text-[12px] text-muted-foreground">
              — {block.source}
            </figcaption>
          ) : null}
        </figure>
      )

    case "divider":
      return (
        <div className="flex items-center gap-3 py-1" aria-hidden>
          <span className="h-px flex-1 bg-border/70" />
          <span className="h-1 w-1 rounded-full bg-border" />
          <span className="h-px flex-1 bg-border/70" />
        </div>
      )

    case "verdict_card": {
      const config = {
        yes: {
          icon: CheckCircle2,
          color: "text-emerald-500",
          bg: "bg-emerald-500/[0.04] border-emerald-500/20",
          text: "Да",
        },
        no: {
          icon: XCircle,
          color: "text-rose-500",
          bg: "bg-rose-500/[0.04] border-rose-500/20",
          text: "Нет",
        },
        maybe: {
          icon: HelpCircle,
          color: "text-purple-500",
          bg: "bg-purple-500/[0.04] border-purple-500/20",
          text: "Возможно",
        },
      }[block.verdict]

      const Icon = config.icon
      const confLabel = CONFIDENCE_LABELS[block.confidenceLabel] ?? "Средняя"

      return (
        <div className={`rounded-2xl border p-5 ${config.bg}`} data-testid="horary-verdict-card">
          <div className="flex items-center gap-3">
            <Icon className={`h-8 w-8 ${config.color}`} />
            <div>
              <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Вердикт
              </div>
              <div className="font-serif text-[22px] font-semibold leading-none mt-1 text-foreground">
                {block.label || config.text}
              </div>
            </div>
          </div>
          <div className="mt-4 space-y-1.5">
            <div
              className="text-[12.5px] text-muted-foreground"
              data-testid="horary-confidence-label"
            >
              <span className="font-medium text-foreground/85">
                {CONFIDENCE_INTRO[block.confidenceLabel]}
              </span>{" "}
              {confLabel}
            </div>
            {block.confidenceExplanation ? (
              <p
                className="text-[12.5px] leading-relaxed text-foreground/75"
                data-testid="horary-confidence-explanation"
              >
                {block.confidenceExplanation}
              </p>
            ) : null}
          </div>
        </div>
      )
    }

    case "testimonies": {
      return (
        <div className="grid gap-2.5" data-testid="horary-testimonies">
          {block.pros && block.pros.length > 0 ? (
            <div className="rounded-2xl border border-border/70 bg-card px-4 py-3.5">
              <div className="mb-2 text-[10.5px] font-medium uppercase tracking-[0.14em] text-primary">
                {block.prosLabel}
              </div>
              <ul className="flex flex-col gap-2">
                {block.pros.map((p, i) => (
                  <TestimonyRow key={`p-${i}`} item={p} positive />
                ))}
              </ul>
            </div>
          ) : null}
          {block.cons && block.cons.length > 0 ? (
            <div className="rounded-2xl border border-border/70 bg-muted/40 px-4 py-3.5">
              <div className="mb-2 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {block.consLabel}
              </div>
              <ul className="flex flex-col gap-2">
                {block.cons.map((c, i) => (
                  <TestimonyRow key={`c-${i}`} item={c} positive={false} />
                ))}
              </ul>
            </div>
          ) : null}
          {block.neutral && block.neutral.length > 0 ? (
            <div className="rounded-2xl border border-dashed border-border/70 bg-secondary/30 px-4 py-3.5">
              <div className="mb-2 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {block.neutralLabel}
              </div>
              <ul className="flex flex-col gap-2">
                {block.neutral.map((n, i) => (
                  <TestimonyRow key={`n-${i}`} item={n} neutral />
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )
    }

    case "timing": {
      const config = timingConfig(block.status)
      const Icon = config.icon
      return (
        <div
          className={`flex gap-3 rounded-2xl border px-4 py-3.5 ${config.wrap}`}
          data-testid="horary-timing"
          data-timing-status={block.status}
        >
          <div
            className={`mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-full ${config.iconWrap}`}
          >
            <Icon className="h-4 w-4" strokeWidth={1.7} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Сроки реализации
            </div>
            {block.status === "known" && block.timeRange ? (
              <div
                className="font-serif text-[17px] font-semibold mt-1"
                data-testid="horary-timing-range"
              >
                {block.timeRange}
              </div>
            ) : null}
            {block.status === "unclear" && block.timeRange ? (
              <div
                className="font-serif text-[16px] font-medium mt-1 text-foreground/85"
                data-testid="horary-timing-range"
              >
                {block.timeRange}
              </div>
            ) : null}
            <p
              className="mt-1 font-serif text-[15px] leading-relaxed text-foreground/80"
              data-testid="horary-timing-text"
            >
              {block.text}
            </p>
          </div>
        </div>
      )
    }

    default:
      return null
  }
}

function TestimonyRow({
  item,
  positive,
  neutral,
}: {
  item: { title: string; explanation: string }
  positive?: boolean
  neutral?: boolean
}) {
  const Icon = neutral ? Info : positive ? Check : AlertTriangle
  const iconClass = neutral
    ? "text-muted-foreground"
    : positive
      ? "text-primary"
      : "text-foreground/50"
  return (
    <li className="flex items-start gap-2.5">
      <Icon className={`mt-0.5 h-4 w-4 flex-none ${iconClass}`} strokeWidth={1.7} />
      <div className="min-w-0 flex-1">
        <div className="text-[14px] font-medium text-foreground/90">
          {item.title}
        </div>
        <div className="text-[13px] leading-relaxed text-foreground/75">
          {item.explanation}
        </div>
      </div>
    </li>
  )
}

function timingConfig(status: "known" | "unclear" | "not_enough_evidence") {
  if (status === "not_enough_evidence") {
    return {
      wrap: "border-border/60 bg-muted/30",
      iconWrap: "bg-muted text-muted-foreground",
      icon: AlertOctagon,
    }
  }
  if (status === "unclear") {
    return {
      wrap: "border-border/70 bg-secondary/[0.05]",
      iconWrap: "bg-secondary text-foreground/70",
      icon: Timer,
    }
  }
  return {
    wrap: "border-border/70 bg-secondary/[0.05]",
    iconWrap: "bg-primary/10 text-primary",
    icon: Timer,
  }
}

function calloutStyles(tone: CalloutTone) {
  switch (tone) {
    case "strength":
      return {
        wrap: "border-primary/25 bg-primary/[0.06]",
        iconWrap: "bg-primary/15 text-primary",
        text: "text-foreground/90",
        icon: Sparkles,
      }
    case "risk":
      return {
        wrap: "border-destructive/25 bg-destructive/[0.05]",
        iconWrap: "bg-destructive/15 text-destructive",
        text: "text-foreground/85",
        icon: AlertTriangle,
      }
    case "insight":
      return {
        wrap: "border-border/70 bg-secondary/50",
        iconWrap: "bg-primary/15 text-primary",
        text: "text-foreground/90",
        icon: Sparkles,
      }
    case "neutral":
    default:
      return {
        wrap: "border-border/70 bg-muted/40",
        iconWrap: "bg-card text-foreground/60",
        text: "text-foreground/80",
        icon: Info,
      }
  }
}
