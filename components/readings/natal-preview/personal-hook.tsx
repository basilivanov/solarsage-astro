"use client"

type Props = {
  text: string
}

export function PersonalHook({ text }: Props) {
  if (!text) return null

  return (
    <blockquote className="rounded-2xl border border-primary/12 bg-gradient-to-br from-primary/[0.04] to-primary/[0.01] px-5 py-4">
      <p className="font-serif text-[17px] leading-relaxed text-foreground/90">
        {text}
      </p>
    </blockquote>
  )
}
