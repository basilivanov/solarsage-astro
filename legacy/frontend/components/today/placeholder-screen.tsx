import type { LucideIcon } from "lucide-react"

export function PlaceholderScreen({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: LucideIcon
  title: string
  subtitle: string
}) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center px-10 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-border/70 bg-card text-muted-foreground">
        <Icon className="h-6 w-6" strokeWidth={1.5} />
      </div>
      <h2 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
        {title}
      </h2>
      <p className="mt-2 max-w-[20ch] text-[13px] leading-relaxed text-muted-foreground">
        {subtitle}
      </p>
      <span className="mt-5 rounded-full border border-border/70 bg-card px-3 py-1 text-[10px] uppercase tracking-[0.14em] text-muted-foreground/80">
        скоро
      </span>
    </div>
  )
}
