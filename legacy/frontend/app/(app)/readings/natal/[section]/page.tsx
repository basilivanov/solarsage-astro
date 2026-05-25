import { notFound } from "next/navigation"

import { NatalSectionView } from "@/components/readings/natal/natal-section"
import { getNatalReport, getNatalSection } from "@/lib/api/natal"

type Params = { section: string }

/**
 * /readings/natal/[section] — отдельная глава разбора.
 *
 * В Next 16 параметры асинхронные. Если глава с таким id отсутствует —
 * показываем 404 (Telegram WebApp обработает это как обычный экран).
 */
export default async function NatalSectionPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { section: id } = await params
  const data = getNatalSection(id)
  if (!data) notFound()

  return (
    <NatalSectionView
      report={data.report}
      section={data.section}
      prev={data.prev}
      next={data.next}
      index={data.index}
      total={data.total}
    />
  )
}

/**
 * Статически известный список глав — пригодится в будущем для prerender.
 * При смене мока на fetch этот хелпер можно убрать или сделать async.
 */
export function generateStaticParams(): Params[] {
  return getNatalReport().sections.map((s) => ({ section: s.id }))
}
