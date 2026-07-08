// Astro history widget — shows historical events for this date.
// Static educational content, not personal astrology or mock API.
import { CalendarDays } from "lucide-react"

type Event = { date: string; label: string; description: string }

const EVENTS: Event[] = [
  { date: "2026-07-05", label: "5 июля", description: "Солнце в Раке — время заботы о доме и семье" },
  { date: "2026-07-06", label: "6 июля", description: "Луна переходит в Деву — внимание к деталям" },
  { date: "2026-07-07", label: "7 июля", description: "Меркурий в трине к Юпитеру — удачные переговоры" },
]

export function AstroHistoryWidget({ date }: { date: Date }) {
  const dateStr = date.toISOString().split("T")[0]
  const todayEvent = EVENTS.find((e) => e.date === dateStr)
  if (!todayEvent) return null

  return (
    <section className="px-5" data-testid="astro-history-widget">
      <div className="rounded-2xl border border-border/50 bg-card/60 p-4">
        <div className="mb-2 flex items-center gap-2">
          <CalendarDays className="h-4 w-4 text-muted-foreground" strokeWidth={1.6} />
          <h3 className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
            В этот день
          </h3>
        </div>
        <div className="space-y-1">
          <p className="text-[13px] font-medium text-foreground">{todayEvent.label}</p>
          <p className="text-[12px] leading-snug text-muted-foreground">{todayEvent.description}</p>
        </div>
      </div>
    </section>
  )
}
