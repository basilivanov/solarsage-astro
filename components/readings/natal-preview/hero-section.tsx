"use client"

type Props = {
  name?: string | null
  ascSign?: string | null
  birthCity?: string | null
  gender: string
}

export function HeroSection({ name, ascSign, birthCity, gender }: Props) {
  const title = name ? `Натальная карта ${name}` : "Твоя натальная карта"
  const subtitleParts = [ascSign ? `ASC в ${ascSign}` : null, birthCity, gender === "female" ? "для неё" : "для него"].filter(Boolean)

  return (
    <section className="rounded-3xl border border-border/70 bg-card px-5 py-6">
      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Natal preview
      </span>
      <h1 className="mt-2 font-serif text-[30px] leading-tight tracking-tight text-foreground">
        {title}
      </h1>
      {subtitleParts.length > 0 ? (
        <p className="mt-3 text-[14px] leading-relaxed text-muted-foreground">
          {subtitleParts.join(" · ")}
        </p>
      ) : null}
    </section>
  )
}
