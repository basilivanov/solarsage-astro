// AI_HEADER
// module: M-COMPONENTS-LOCKED-FEATURE
// purpose: Unified locked/coming-soon placeholder for closed features

type Props = {
  title: string
  description: string
  badge?: "Скоро" | "Закрыто"
}

export function LockedFeatureCard({ title, description, badge = "Скоро" }: Props) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-5">
      <div className="flex w-full max-w-sm flex-col items-center text-center gap-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-secondary/60">
          <span className="font-serif text-[22px] text-muted-foreground/60">✦</span>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-center gap-2">
            <span className="rounded-full bg-accent/20 px-3 py-0.5 font-sans text-[11px] font-medium uppercase tracking-[0.14em] text-accent-foreground/70">
              {badge}
            </span>
          </div>
          <h1 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
            {title}
          </h1>
        </div>

        <p className="max-w-[32ch] font-sans text-[15px] leading-relaxed text-muted-foreground text-pretty">
          {description}
        </p>
      </div>
    </div>
  )
}
