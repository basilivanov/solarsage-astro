"use client"

import Link from "next/link"

type Props = {
  missingFields: string[]
}

export function ProfileIncompleteCard({ missingFields }: Props) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card p-5">
      <h1 className="font-serif text-[24px] leading-tight text-foreground">Нужно заполнить профиль</h1>
      {missingFields.length ? (
        <ul className="mt-3 space-y-2 text-[13px] leading-relaxed text-muted-foreground">
          {missingFields.map((field) => (
            <li key={field}>• {field}</li>
          ))}
        </ul>
      ) : null}
      <Link
        href="/readings"
        className="mt-4 inline-flex rounded-xl bg-primary px-4 py-2 text-[13px] font-medium text-primary-foreground"
      >
        Назад к разборам
      </Link>
    </div>
  )
}
