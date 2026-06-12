
// ############################################################################
// AI_HEADER: MODULE_NATAL_BLOCK_RENDERER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: block-renderer.tsx
// owns:
//   - components/readings/natal/block-renderer.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { Check, Sparkles, AlertTriangle, Info, Quote } from "lucide-react"

import type { Block, CalloutTone, NatalReport } from "@/lib/contracts/natal"
import { SpheresWidget } from "./widgets/spheres-widget"
import { PlanetsWidget } from "./widgets/planets-widget"

type Props = {
  block: Block
  /**
   * Полный отчёт нужен только для встроенных виджетов
   * (spheres_widget / planets_widget) — они читают meta-данные.
   * Если виджеты в этом блоке не используются, поле можно не передавать.
   */
  report?: NatalReport
}

/**
 * Универсальный рендерер блока.
 *
 * Контракт блоков дискриминирован по `type`. Здесь мы маппим тип →
 * компонент. Если приходит неизвестный тип (новый бэк, старый фронт),
 * блок молча пропускается — это страховка обратной совместимости,
 * прописанная в `natal-schema`.
 */
export function BlockRenderer({ block, report }: Props) {
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
          {block.items.map((item: string, i: number) => (
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
      const styles = calloutStyles(tone)
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
                {block.pros.map((p: string, i: number) => (
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
                {block.cons.map((c: string, i: number) => (
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

    case "stat_grid":
      return (
        <div className="grid grid-cols-2 gap-2">
          {block.items.map((item: { label: string; value: string }, i: number) => (
            <div
              key={i}
              className="rounded-xl border border-border/60 bg-card px-3.5 py-2.5"
            >
              <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {item.label}
              </div>
              <div className="mt-0.5 font-serif text-[15px] leading-tight text-foreground">
                {item.value}
              </div>
            </div>
          ))}
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
          {block.cite ? (
            <figcaption className="mt-2 text-[12px] text-muted-foreground">
              — {block.cite}
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

    case "spheres_widget":
      if (!report?.spheres) return null
      return <SpheresWidget spheres={report.spheres} limit={block.limit} />

    case "planets_widget":
      if (!report?.planets) return null
      return <PlanetsWidget planets={report.planets} />

    default:
      // Неизвестный тип — мягкая деградация. Это часть контракта:
      // фронт не падает, если бэк ввёл новый блок раньше нас.
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
