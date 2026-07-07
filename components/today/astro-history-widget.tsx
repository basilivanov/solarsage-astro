// ############################################################################
// AI_HEADER: MODULE_TODAY_ASTRO_HISTORY_WIDGET — static astronomy history card.
// ROLE: Educational UI component for the bottom of /day/[date]. It displays
//       curated astronomy/history events by date and does not simulate API data.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-ASTRO-HISTORY-WIDGET
// purpose: Render a deterministic educational history card for the selected
//          date. Called by TodayScreen after WeekStrip and before disclaimer.
// owns:
//   - components/today/astro-history-widget.tsx
// inputs: date?: Date — selected day for exact or nearby curated events.
// outputs: TSX section with data-testid="astro-history-widget", or null.
// dependencies:
//   - lucide-react
// side_effects: none
// emitted_logs: none
// invariants:
//   - Content is static curated astronomy/space-history copy.
//   - No runtime mocks, demo backend data, or personal astrology fabrication.
// failure_policy: Returns null when no exact or nearby curated event exists.
// END_MODULE_CONTRACT: M-TODAY-ASTRO-HISTORY-WIDGET

"use client"

import { BookOpen, ChevronRight, Star } from "lucide-react"

type AstroEvent = {
  month: number
  day: number
  year: number
  title: string
  description: string
  category: "discovery" | "mission" | "memory" | "event"
}

const EVENTS: AstroEvent[] = [
  { month: 0, day: 7, year: 1610, title: "Галилей открыл спутники Юпитера", description: "Галилео Галилей впервые наблюдал Ио, Европу, Ганимед и Каллисто.", category: "discovery" },
  { month: 0, day: 3, year: 1959, title: "«Луна-1» вышла к межпланетному пространству", description: "Советская станция стала первым искусственным объектом на гелиоцентрической орбите.", category: "mission" },
  { month: 1, day: 18, year: 1930, title: "Клайд Томбо открыл Плутон", description: "Плутон нашли на снимках обсерватории Ловелла.", category: "discovery" },
  { month: 1, day: 20, year: 1962, title: "Первый американец на орбите", description: "Джон Гленн совершил орбитальный полет на корабле «Френдшип-7».", category: "mission" },
  { month: 2, day: 13, year: 1781, title: "Уильям Гершель открыл Уран", description: "Седьмая планета стала первой планетой, открытой с помощью телескопа.", category: "discovery" },
  { month: 2, day: 24, year: 1993, title: "Первый объект пояса Койпера после Плутона", description: "Дэвид Джуитт и Джейн Лу открыли объект 1992 QB1.", category: "discovery" },
  { month: 3, day: 12, year: 1961, title: "Юрий Гагарин в космосе", description: "Корабль «Восток-1» совершил первый пилотируемый космический полет.", category: "mission" },
  { month: 3, day: 24, year: 1990, title: "Запуск телескопа «Хаббл»", description: "Орбитальная обсерватория изменила наблюдательную астрономию.", category: "mission" },
  { month: 4, day: 5, year: 1961, title: "Первый американец в космосе", description: "Алан Шепард совершил суборбитальный полет на «Меркурий-3».", category: "mission" },
  { month: 4, day: 29, year: 1919, title: "Проверка общей теории относительности", description: "Экспедиция Эддингтона подтвердила отклонение света гравитацией Солнца.", category: "event" },
  { month: 5, day: 18, year: 1983, title: "Салли Райд в космосе", description: "Салли Райд стала первой американской женщиной-астронавтом.", category: "mission" },
  { month: 5, day: 22, year: 1978, title: "Открытие Харона", description: "Джеймс Кристи обнаружил крупнейший спутник Плутона.", category: "discovery" },
  { month: 5, day: 30, year: 1908, title: "Тунгусское событие", description: "В Сибири произошел мощный взрыв, связанный с падением космического тела.", category: "event" },
  { month: 6, day: 4, year: 1997, title: "«Марс Пасфайндер» на Марсе", description: "Зонд успешно посадил марсоход «Соджорнер», первый rover на Марсе.", category: "mission" },
  { month: 6, day: 20, year: 1969, title: "Высадка на Луну", description: "Нил Армстронг и Базз Олдрин ступили на поверхность Луны.", category: "mission" },
  { month: 7, day: 24, year: 2006, title: "Плутон стал карликовой планетой", description: "Международный астрономический союз обновил классификацию Плутона.", category: "event" },
  { month: 7, day: 25, year: 1981, title: "«Вояджер-2» у Сатурна", description: "Аппарат передал детальные изображения колец и спутников Сатурна.", category: "mission" },
  { month: 8, day: 1, year: 1979, title: "«Пионер-11» у Сатурна", description: "Аппарат первым исследовал Сатурн с близкого расстояния.", category: "mission" },
  { month: 8, day: 23, year: 1846, title: "Открытие Нептуна", description: "Иоганн Галле нашел Нептун по математическим расчетам Леверье.", category: "discovery" },
  { month: 9, day: 4, year: 1957, title: "Запуск первого спутника", description: "«Спутник-1» открыл космическую эру.", category: "mission" },
  { month: 9, day: 19, year: 2017, title: "Открыт «Оумуамуа»", description: "Астрономы обнаружили первый известный межзвездный объект в Солнечной системе.", category: "discovery" },
  { month: 10, day: 12, year: 2014, title: "«Фила» на комете", description: "Модуль миссии «Розетта» впервые мягко сел на ядро кометы.", category: "mission" },
  { month: 10, day: 27, year: 1971, title: "«Маринер-9» у Марса", description: "Аппарат стал первым искусственным спутником Марса.", category: "mission" },
  { month: 11, day: 14, year: 1972, title: "Последний человек на Луне", description: "Эжен Сернан покинул поверхность Луны в миссии «Аполлон-17».", category: "mission" },
  { month: 11, day: 21, year: 1968, title: "«Аполлон-8» отправился к Луне", description: "Это был первый пилотируемый корабль, покинувший околоземную орбиту.", category: "mission" },
]

const CATEGORY_META: Record<AstroEvent["category"], { label: string; color: string; Icon: typeof Star }> = {
  discovery: { label: "открытие", color: "oklch(0.70 0.13 85)", Icon: Star },
  mission: { label: "миссия", color: "oklch(0.62 0.06 305)", Icon: BookOpen },
  memory: { label: "память", color: "oklch(0.65 0.10 150)", Icon: Star },
  event: { label: "событие", color: "oklch(0.60 0.10 230)", Icon: BookOpen },
}

type Props = {
  date?: Date
}

// START_BLOCK: SELECT_HISTORY_EVENT
function selectHistoryEvent(date: Date): { event: AstroEvent; exact: boolean } | null {
  // START_FUNCTION_CONTRACT: F-M-TODAY-ASTRO-HISTORY-WIDGET.selectHistoryEvent
  // purpose: Select the closest curated event for the given month/day.
  // inputs: date — selected calendar day.
  // returns: event/exact pair, or null when no curated event is nearby.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Never throws intentionally for valid Date objects.
  // END_FUNCTION_CONTRACT: F-M-TODAY-ASTRO-HISTORY-WIDGET.selectHistoryEvent
  const month = date.getMonth()
  const day = date.getDate()
  const exact = EVENTS.filter((event) => event.month === month && event.day === day)
    .sort((a, b) => b.year - a.year)[0]
  if (exact) return { event: exact, exact: true }

  const near = EVENTS.filter((event) => event.month === month && Math.abs(event.day - day) <= 3)
    .sort((a, b) => Math.abs(a.day - day) - Math.abs(b.day - day) || b.year - a.year)[0]
  return near ? { event: near, exact: false } : null
}
// END_BLOCK: SELECT_HISTORY_EVENT

// START_BLOCK: ASTRO_HISTORY_WIDGET_COMPONENT
export function AstroHistoryWidget({ date = new Date() }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-ASTRO-HISTORY-WIDGET.AstroHistoryWidget
  // purpose: Render the educational history widget for the selected date.
  // inputs: Props.date — selected route date.
  // returns: JSX.Element | null.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Returns null when no curated content matches.
  // END_FUNCTION_CONTRACT: F-M-TODAY-ASTRO-HISTORY-WIDGET.AstroHistoryWidget
  const selected = selectHistoryEvent(date)
  if (!selected) return null

  const meta = CATEGORY_META[selected.event.category]
  const Icon = meta.Icon

  return (
    <section className="px-5" aria-label="Астрономическая история" data-testid="astro-history-widget">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {selected.exact ? "В этот день" : "Ближайшие дни"}
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <article
        className="relative overflow-hidden rounded-2xl border p-4"
        style={{
          borderColor: `${meta.color}30`,
          background: `linear-gradient(135deg, ${meta.color}0a, transparent 70%)`,
        }}
      >
        <div aria-hidden className="pointer-events-none absolute right-0 top-0 h-28 w-28 opacity-20">
          {[14, 38, 62, 82].map((top, index) => (
            <span
              key={`${top}-${index}`}
              className="absolute h-0.5 w-0.5 rounded-full"
              style={{ right: `${12 + index * 16}%`, top: `${top}%`, background: meta.color }}
            />
          ))}
        </div>

        <div className="relative">
          <div className="mb-2 flex items-center gap-2">
            <span className="font-serif text-[28px] leading-none" style={{ color: meta.color }}>
              {selected.event.year}
            </span>
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider"
              style={{ background: `${meta.color}14`, color: meta.color }}
            >
              <Icon className="h-2.5 w-2.5" strokeWidth={2} aria-hidden />
              {meta.label}
            </span>
          </div>

          <h3 className="font-serif text-[17px] leading-tight text-foreground">
            {selected.event.title}
          </h3>
          <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
            {selected.event.description}
          </p>
          {!selected.exact ? (
            <div className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
              Событие рядом с выбранной датой
              <ChevronRight className="h-3 w-3" strokeWidth={2} aria-hidden />
            </div>
          ) : null}
        </div>
      </article>
    </section>
  )
}
// END_BLOCK: ASTRO_HISTORY_WIDGET_COMPONENT
