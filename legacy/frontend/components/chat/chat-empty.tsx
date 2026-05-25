import { Sparkles } from "lucide-react"
import type { ReactNode } from "react"

/**
 * Пустое состояние чата.
 *
 * Здесь короткое объяснение, чем ассистент отличается от обычного ИИ
 * (он знает натальную карту), и слот под список стартовых подсказок.
 */
export function ChatEmpty({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-5 pb-3 pt-1">
      <div className="flex items-start gap-3 rounded-2xl border border-border/70 bg-card px-4 py-4">
        <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-secondary text-primary">
          <Sparkles className="h-[18px] w-[18px]" strokeWidth={1.6} />
        </div>
        <div className="space-y-1">
          <p className="font-serif text-[18px] leading-snug text-foreground text-balance">
            Личный астролог-ассистент
          </p>
          <p className="text-[13px] leading-snug text-muted-foreground text-pretty">
            Я знаю твою натальную карту и текущие транзиты. Спроси про
            карьеру, отношения, важные дни — отвечу с учётом именно
            твоей карты.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className="px-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
          Можно начать так
        </p>
        {children}
      </div>
    </div>
  )
}
