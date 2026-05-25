import { NatalToc } from "@/components/readings/natal/natal-toc"
import { getNatalReport } from "@/lib/api/natal"

/**
 * /readings/natal — оглавление глубокого разбора натальной карты.
 *
 * Сервер-рендер: данные приходят из мока `getNatalReport`, который
 * в будущем заменится на fetch к движку. Контракт `NatalReport` от этого
 * не меняется — UI остаётся тем же.
 */
export default function NatalReadingPage() {
  const report = getNatalReport()
  return <NatalToc report={report} />
}
