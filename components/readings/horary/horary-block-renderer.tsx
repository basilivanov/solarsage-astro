"use client"

import { Check, Sparkles, AlertTriangle, Info, Quote, CheckCircle2, XCircle, HelpCircle, Timer } from "lucide-react"
import type { HoraryBlock } from "@/lib/contracts/horary"
import type { CalloutTone } from "@/lib/contracts/natal"

type Props = {
  block: HoraryBlock
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

      return (
        <div className={`rounded-2xl border p-5 ${config.bg}`}>
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
          <div className="mt-4">
            <div className="flex justify-between text-[12px] text-muted-foreground mb-1">
              <span>Уверенность звёзд</span>
              <span>{Math.round(block.confidence * 100)}%</span>
            </div>
            <div className="h-1.5 w-full bg-border/40 rounded-full overflow-hidden">
              <div
                className={`h-full ${config.color.replace("text-", "bg-")}`}
                style={{ width: `${block.confidence * 100}%` }}
              />
            </div>
          </div>
        </div>
      )
    }

    case "timing":
      return (
        <div className="flex gap-3 rounded-2xl border border-border/70 bg-secondary/[0.05] px-4 py-3.5">
          <div className="mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-full bg-primary/10 text-primary">
            <Timer className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Сроки реализации
            </div>
            <div className="font-serif text-[17px] font-semibold mt-1">
              {block.timeRange}
            </div>
            {block.text ? (
              <p className="mt-1 font-serif text-[15px] leading-relaxed text-foreground/80">
                {block.text}
              </p>
            ) : null}
          </div>
        </div>
      )

    default:
      return null
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
