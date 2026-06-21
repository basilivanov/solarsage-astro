"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Star, BookOpen, ChevronRight } from "lucide-react"

/**
 * AstroHistoryWidget — "В этот день в истории астрологии".
 *
 * Shows notable astronomical and astrological events that happened on
 * this day in history. Purely educational content — adds engagement
 * and gives users a reason to return daily.
 *
 * Data is a static curated list of ~20 events; the widget picks the
 * ones matching the current month+day.
 */

interface AstroEvent {
  month: number // 0-indexed
  day: number
  year: number
  title: string
  description: string
  category: "discovery" | "mission" | "birth" | "event"
}

const EVENTS: AstroEvent[] = [
  // January
  { month: 0, day: 7, year: 1610, title: "Галилей открыл спутники Юпитера", description: "Галилео Галилей впервые наблюдал четыре крупнейших спутника Юпитера — Ио, Европу, Ганимед и Каллисто. Это перевернуло представление о строении Вселенной.", category: "discovery" },
  { month: 0, day: 3, year: 1959, title: "«Луна-1» — первый космический аппарат", description: "Советская станция «Луна-1» стала первым искусственным объектом, преодолевшим гравитацию Земли и вышедшим на гелиоцентрическую орбиту.", category: "mission" },

  // February
  { month: 1, day: 18, year: 1930, title: "Клайд Томбо открыл Плутон", description: "Американский астроном Клайд Томбо обнаружил Плутон на снимках, сделанных в обсерватории Ловелла. Открытие было объявлено 13 марта.", category: "discovery" },
  { month: 1, day: 20, year: 1962, title: "Первый американец на орбите", description: "Джон Гленн стал первым американцем, совершившим орбитальный космический полёт на корабле «Френдшип-7».", category: "mission" },

  // March
  { month: 2, day: 13, year: 1781, title: "Уильям Гершель открыл Уран", description: "Британский астроном Уильям Гершель обнаружил седьмую планету Солнечной системы — Уран. Это была первая планета, открытая с помощью телескопа.", category: "discovery" },
  { month: 2, day: 24, year: 1993, title: "Открытие первого объекта пояса Койпера", description: "Астрономы Дэвид Джуитт и Джейн Лу открыли 1992 QB1 — первый объект пояса Койпера после Плутона.", category: "discovery" },

  // April
  { month: 3, day: 12, year: 1961, title: "Юрий Гагарин в космосе", description: "Юрий Гагарин стал первым человеком, совершившим полёт в космос на корабле «Восток-1». Полёт длился 108 минут.", category: "mission" },
  { month: 3, day: 24, year: 1990, title: "Запуск телескопа «Хаббл»", description: "Космический телескоп «Хаббл» был выведен на орбиту шаттлом «Дискавери». Он произвёл революцию в наблюдательной астрономии.", category: "mission" },

  // May
  { month: 4, day: 5, year: 1961, title: "Первый американец в космосе", description: "Алан Шепард совершил 15-минутный суборбитальный полёт на корабле «Меркурий-3».", category: "mission" },
  { month: 4, day: 29, year: 1919, title: "Проверка общей теории относительности", description: "Экспедиция Эддингтона наблюдала полное солнечное затмение и подтвердила отклонение света звёзд гравитацией Солнца — предсказание Эйнштейна.", category: "event" },

  // June
  { month: 5, day: 20, year: 1670, title: "Николя Клод Фабри де Пейреск умер", description: "Французский астроном, впервые описавший туманность Ориона в 1610 году, в те же дни, что и Галилей.", category: "birth" },
  { month: 5, day: 18, year: 1983, title: "Салли Райд — первая американка в космосе", description: "Салли Райд совершила полёт на шаттле «Челленджер», став первой американской женщиной-астронавтом.", category: "mission" },
  { month: 5, day: 22, year: 1978, title: "Открытие Харона — спутника Плутона", description: "Американский астроном Джеймс Кристи обнаружил Харон, крупнейший спутник Плутона, на снимках обсерватории Флагстафф.", category: "discovery" },
  { month: 5, day: 30, year: 1908, title: "Тунгусский метеорит", description: "В районе реки Подкаменная Тунгуска произошёл мощный взрыв, предположительно вызванный падением метеороида. Энергия взрыва оценивается в 10–15 мегатонн.", category: "event" },

  // July
  { month: 6, day: 20, year: 1969, title: "Высадка на Луну", description: "Нил Армстронг и Базз Олдрин стали первыми людьми, ступившими на поверхность Луны в ходе миссии «Аполлон-11».", category: "mission" },
  { month: 6, day: 4, year: 1997, title: "«Марс Пасфайндер» на Марсе", description: "Американский зонд «Марс Пасфайндер» успешно посадил марсоход «Соджорнер» — первый rover на Марсе.", category: "mission" },

  // August
  { month: 7, day: 25, year: 1981, title: "«Вояджер-2» пролетел Сатурн", description: "Космический аппарат «Вояджер-2» прошёл вблизи Сатурна, передав детальные изображения колец и спутников.", category: "mission" },
  { month: 7, day: 24, year: 2006, title: "Плутон лишился статуса планеты", description: "МАС (Международный астрономический союз) перевёл Плутон в категорию «карликовых планет».", category: "event" },

  // September
  { month: 8, day: 1, year: 1979, title: "«Пионер-11» у Сатурна", description: "Аппарат «Пионер-11» стал первым искусственным объектом, исследовавшим Сатурн с близкого расстояния.", category: "mission" },
  { month: 8, day: 23, year: 1846, title: "Открытие Нептуна", description: "Немецкий астроном Иоганн Галле открыл Нептун, опираясь на математические предсказания Леверье. Это была первая планета, найденная «на кончике пера».", category: "discovery" },

  // October
  { month: 9, day: 4, year: 1957, title: "Запуск первого спутника", description: "СССР запустил «Спутник-1» — первый искусственный спутник Земли. Это положило начало космической эре.", category: "mission" },
  { month: 9, day: 19, year: 2017, title: "«Оумуамуа» — первый межзвёздный объект", description: "Астрономы обнаружили 1I/2017 U1 («Оумуамуа») — первый известный межзвёздный объект, пролетевший через Солнечную систему.", category: "discovery" },

  // November
  { month: 10, day: 12, year: 2014, title: "«Фила» на комете", description: "Посадочный модуль «Фила» миссии «Розетта» совершил первую в истории мягкую посадку на ядро кометы 67P/Чурюмова–Герасименко.", category: "mission" },
  { month: 10, day: 27, year: 1971, title: "«Маринер-9» на орбите Марса", description: "Американский зонд «Маринер-9» стал первым искусственным спутником Марса.", category: "mission" },

  // December
  { month: 11, day: 14, year: 1972, title: "Последний человек на Луне", description: "Эжен Сернан покинул поверхность Луны в ходе миссии «Аполлон-17» — до сих пор последний человек, побывавший на Луне.", category: "mission" },
  { month: 11, day: 21, year: 1968, title: "«Аполлон-8» — к Луне", description: "«Аполлон-8» стал первым пилотируемым кораблём, покинувшим околоземную орбиту и отправившимся к Луне.", category: "mission" },
]

const CATEGORY_META: Record<string, { label: string; color: string; icon: typeof Star }> = {
  discovery: { label: "Открытие", color: "oklch(0.70 0.13 85)", icon: Star },
  mission: { label: "Миссия", color: "oklch(0.62 0.06 305)", icon: BookOpen },
  birth: { label: "Память", color: "oklch(0.65 0.10 150)", icon: Star },
  event: { label: "Событие", color: "oklch(0.60 0.10 230)", icon: BookOpen },
}

interface AstroHistoryWidgetProps {
  date?: Date
}

export function AstroHistoryWidget({ date }: AstroHistoryWidgetProps) {
  const [expanded, setExpanded] = useState(false)

  const target = useMemo(() => date ?? new Date(), [date])

  const todaysEvents = useMemo(() => {
    const month = target.getMonth()
    const day = target.getDate()
    // First, try exact match
    const exact = EVENTS.filter((e) => e.month === month && e.day === day).sort((a, b) => b.year - a.year)
    if (exact.length > 0) return exact

    // If no exact match, find events within ±3 days this month
    const near = EVENTS.filter((e) => {
      if (e.month !== month) return false
      const diff = Math.abs(e.day - day)
      return diff <= 3 && diff > 0
    }).sort((a, b) => {
      // Sort by proximity to today
      const diffA = Math.abs(a.day - day)
      const diffB = Math.abs(b.day - day)
      return diffA - diffB || b.year - a.year
    })
    return near
  }, [target])

  if (todaysEvents.length === 0) return null

  const primary = todaysEvents[0]
  const rest = todaysEvents.slice(1)
  const cat = CATEGORY_META[primary.category]

  // Check if the primary event is today or nearby
  const month = target.getMonth()
  const day = target.getDate()
  const isExact = primary.month === month && primary.day === day
  const headerLabel = isExact ? "В этот день" : "Ближайшие дни"

  return (
    <section className="px-6" aria-label="В этот день в истории">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {headerLabel}
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative overflow-hidden rounded-2xl border p-4"
        style={{
          borderColor: `${cat.color}30`,
          background: `linear-gradient(135deg, ${cat.color}0a, transparent 70%)`,
        }}
      >
        {/* decorative star pattern */}
        <div aria-hidden className="pointer-events-none absolute right-0 top-0 h-32 w-32 opacity-20">
          {[15, 40, 65, 85, 25, 70].map((top, i) => (
            <motion.span
              key={i}
              className="absolute h-0.5 w-0.5 rounded-full"
              style={{ right: `${10 + i * 12}%`, top: `${top}%`, background: cat.color }}
              animate={{ opacity: [0.2, 0.8, 0.2] }}
              transition={{ duration: 2 + i * 0.3, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>

        <div className="relative">
          {/* Year + category badge */}
          <div className="mb-2 flex items-center gap-2">
            <span
              className="font-serif text-[28px] leading-none"
              style={{ color: cat.color }}
            >
              {primary.year}
            </span>
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider"
              style={{ background: `${cat.color}14`, color: cat.color }}
            >
              <cat.icon className="h-2.5 w-2.5" strokeWidth={2} />
              {cat.label}
            </span>
          </div>

          {/* Title */}
          <h4 className="font-serif text-[17px] leading-tight text-foreground">
            {primary.title}
          </h4>

          {/* Description */}
          <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
            {primary.description}
          </p>

          {/* Expand for more events */}
          {rest.length > 0 && (
            <>
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground transition hover:text-foreground"
              >
                {expanded ? "Свернуть" : `Ещё ${rest.length} ${rest.length === 1 ? "событие" : "события"}`}
                <ChevronRight
                  className="h-3 w-3 transition-transform"
                  style={{ transform: expanded ? "rotate(90deg)" : "rotate(0)" }}
                  strokeWidth={2}
                />
              </button>

              <AnimatePresence>
                {expanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-3 space-y-3 border-t border-border/40 pt-3">
                      {rest.map((e, i) => {
                        const eCat = CATEGORY_META[e.category]
                        return (
                          <div key={i} className="flex gap-3">
                            <span
                              className="font-serif text-[16px] leading-none flex-none pt-0.5"
                              style={{ color: eCat.color }}
                            >
                              {e.year}
                            </span>
                            <div className="min-w-0">
                              <div className="text-[12px] font-medium text-foreground">
                                {e.title}
                              </div>
                              <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                                {e.description}
                              </p>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </div>
      </motion.div>
    </section>
  )
}
