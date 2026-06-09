"use client"

type Props = {
  text: string
}

export function PersonalHook({ text }: Props) {
  if (!text) return null

  return (
    <blockquote className="rounded-2xl border border-primary/15 bg-primary/5 px-4 py-4 font-serif text-[19px] leading-relaxed text-foreground">
      {text}
    </blockquote>
  )
}
