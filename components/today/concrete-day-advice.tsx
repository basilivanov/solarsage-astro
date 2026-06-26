"use client"

import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Zap, ChevronDown } from "lucide-react"
import { computeMoonPhase, getLunarDay, getVoidOfCourse } from "@/lib/moon"
import { getAllRetrogrades } from "@/lib/retrograde"
import type { EnergyItem } from "./day-energy-meter"

/**
 * ConcreteDayAdvice — конкретные однострочные советы по сферам,
 * сгенерированные из реальных расчётных данных (планеты, аспекты,
 * ретрограды, VoC, лунный день, управитель дня).
 *
 * Не шаблоны — каждая строка вычисляется из фактического состояния.
 */

type DayStatus = "steady" | "supportive" | "tense"

interface ConcreteDayAdviceProps {
  date: Date
  dayStatus: DayStatus
  energyItems: EnergyItem[]
}

type Verdict = "good" | "caution" | "avoid" | "neutral"

interface Advice {
  sphere: string
  icon: string
  verdict: Verdict
  text: string
}

function planetStrength(items: EnergyItem[], name: string): number {
  const item = items.find((i) => i.name === name)
  return item?.strength ?? 0.5
}

function isStrong(items: EnergyItem[], name: string): boolean {
  return planetStrength(items, name) >= 0.7
}

function daySeed(date: Date): number {
  return Math.floor(date.getTime() / 86400000)
}

function pick<T>(arr: T[], seed: number): T {
  return arr[Math.abs(seed) % arr.length]
}

function generateAdvice(
  date: Date,
  dayStatus: DayStatus,
  energyItems: EnergyItem[],
): Advice[] {
  const moon = computeMoonPhase(date)
  const lunarDay = getLunarDay(date)
  const voc = getVoidOfCourse(date)
  const retrogrades = getAllRetrogrades(date)
  const seed = daySeed(date)

  const mercuryRx = retrogrades.find((r) => r.planet === "Mercury")?.isRetrograde ?? false
  const venusRx = retrogrades.find((r) => r.planet === "Venus")?.isRetrograde ?? false
  const marsRx = retrogrades.find((r) => r.planet === "Mars")?.isRetrograde ?? false

  const mercuryStrong = isStrong(energyItems, "Mercury")
  const venusStrong = isStrong(energyItems, "Venus")
  const marsStrong = isStrong(energyItems, "Mars")
  const jupiterStrong = isStrong(energyItems, "Jupiter")
  const saturnStrong = isStrong(energyItems, "Saturn")
  const sunStrong = isStrong(energyItems, "Sun")
  const moonStrong = isStrong(energyItems, "Moon")

  const advice: Advice[] = []

  // 1. Работа
  if (marsRx) {
    advice.push({ sphere: "Работа", icon: "💼", verdict: "caution", text: "Новые проекты буксуют — не запускай, дорабатывай текущее" })
  } else if (jupiterStrong && !voc.isVoid) {
    advice.push({ sphere: "Работа", icon: "💼", verdict: "good", text: pick(["Дела летят — запускай масштабное сегодня", "Новые задачи идут легко, не упускай момент"], seed) })
  } else if (saturnStrong) {
    advice.push({ sphere: "Работа", icon: "💼", verdict: "caution", text: "Дела идут со скрипом — не торопись, дойдёт к вечеру" })
  } else if (dayStatus === "tense") {
    advice.push({ sphere: "Работа", icon: "💼", verdict: "caution", text: "Препятствия на ровном месте — делай одно дело за раз" })
  } else {
    advice.push({ sphere: "Работа", icon: "💼", verdict: "neutral", text: "Ровный рабочий день — без сюрпризов, без прорывов" })
  }

  // 2. Деньги
  if (venusStrong && !venusRx) {
    advice.push({ sphere: "Деньги", icon: "💰", verdict: "good", text: pick(["Деньги могут прийти через партнёрство или подарок", "Хороший день для вложений в себя и дом"], seed + 1) })
  } else if (marsRx) {
    advice.push({ sphere: "Деньги", icon: "💰", verdict: "good", text: "Закрой старый долг — вернётся легко. Новый не бери" })
  } else if (saturnStrong) {
    advice.push({ sphere: "Деньги", icon: "💰", verdict: "caution", text: "Сократи траты — день для финансовой дисциплины" })
  } else if (mercuryRx) {
    advice.push({ sphere: "Деньги", icon: "💰", verdict: "caution", text: "Не делай крупных покупок — перепроверь цену завтра" })
  } else {
    advice.push({ sphere: "Деньги", icon: "💰", verdict: "neutral", text: "Стабильно, без неожиданностей — можно планировать бюджет" })
  }

  // 3. Документы
  if (mercuryRx) {
    advice.push({ sphere: "Документы", icon: "📝", verdict: "avoid", text: "Не подписывай контракты — перечитай через 3 дня" })
  } else if (voc.isVoid) {
    advice.push({ sphere: "Документы", icon: "📝", verdict: "avoid", text: "Луна без курса — не подписывай важное до завтра" })
  } else if (mercuryStrong && !mercuryRx) {
    advice.push({ sphere: "Документы", icon: "📝", verdict: "good", text: "Хорошее время для договоров — читай спокойно, подписывай" })
  } else {
    advice.push({ sphere: "Документы", icon: "📝", verdict: "neutral", text: "Обычный день для бумаг — ничего не мешает, но и не помогает" })
  }

  // 4. Отношения
  if (venusRx) {
    advice.push({ sphere: "Отношения", icon: "💖", verdict: "caution", text: "Не начинай новый роман — старые чувства могут вернуться" })
  } else if (venusStrong) {
    advice.push({ sphere: "Отношения", icon: "💖", verdict: "good", text: pick(["Свидания пройдут отлично — будь открыт и смел", "Партнёр будет на твоей стороне — проси поддержки"], seed + 2) })
  } else if (moonStrong && (moon.signName === "Рак" || moon.signName === "Лев" || moon.signName === "Весы")) {
    advice.push({ sphere: "Отношения", icon: "💖", verdict: "good", text: "Эмоциональный контакт глубокий — важные разговоры удаются" })
  } else if (dayStatus === "tense") {
    advice.push({ sphere: "Отношения", icon: "💖", verdict: "caution", text: "Легко поссориться на пустом — держи паузу перед ответом" })
  } else {
    advice.push({ sphere: "Отношения", icon: "💖", verdict: "neutral", text: "Спокойный день для близких — без драмы, без озарений" })
  }

  // 5. Спорт
  if (marsRx) {
    advice.push({ sphere: "Спорт", icon: "🏃", verdict: "caution", text: "Снизь нагрузку — риск травм выше, работай на технику" })
  } else if (marsStrong) {
    advice.push({ sphere: "Спорт", icon: "🏃", verdict: "good", text: pick(["Тренировка будет мощной — ставь рекорд", "Энергия бьёт ключом — иди на максимум"], seed + 3) })
  } else if (sunStrong) {
    advice.push({ sphere: "Спорт", icon: "🏃", verdict: "good", text: "Хороший день для активности — тело готово к нагрузке" })
  } else if (saturnStrong) {
    advice.push({ sphere: "Спорт", icon: "🏃", verdict: "caution", text: "Дисциплинированная тренировка — без рекордов, на выносливость" })
  } else {
    advice.push({ sphere: "Спорт", icon: "🏃", verdict: "neutral", text: "Обычная нагрузка — не перегружай, но и не пропускай" })
  }

  // 6. Общение
  if (mercuryRx) {
    advice.push({ sphere: "Общение", icon: "💬", verdict: "caution", text: "Разговоры путаются — подтверждай всё письменно" })
  } else if (mercuryStrong) {
    advice.push({ sphere: "Общение", icon: "💬", verdict: "good", text: pick(["Переговоры пройдут гладко — проси что хочешь", "Слова сегодня убедительны — договаривайся"], seed + 4) })
  } else if (voc.isVoid) {
    advice.push({ sphere: "Общение", icon: "💬", verdict: "caution", text: "Не назначай важные встречи — решения будут нетвёрдыми" })
  } else {
    advice.push({ sphere: "Общение", icon: "💬", verdict: "neutral", text: "Обычные разговоры — без конфликтов, но и без прорывов" })
  }

  // 7. Здоровье
  if (marsStrong && !marsRx) {
    advice.push({ sphere: "Здоровье", icon: "🌿", verdict: "good", text: "Тело полно сил — хороший день для очищения и процедур" })
  } else if (saturnStrong) {
    advice.push({ sphere: "Здоровье", icon: "🌿", verdict: "caution", text: "Береги суставы и кости — не переохлаждайся" })
  } else if (moon.signName === "Рыбы" || moon.signName === "Скорпион") {
    advice.push({ sphere: "Здоровье", icon: "🌿", verdict: "caution", text: "Чувствительность повышена — береги нервы и сон" })
  } else if (lunarDay.tag === "напряжённый") {
    advice.push({ sphere: "Здоровье", icon: "🌿", verdict: "caution", text: "Лунный день напряжённый — меньше стимуляторов, больше воды" })
  } else {
    advice.push({ sphere: "Здоровье", icon: "🌿", verdict: "neutral", text: "Стабильно — поддерживай режим, ничего особого" })
  }

  // 8. Решения
  if (voc.isVoid) {
    advice.push({ sphere: "Решения", icon: "🎯", verdict: "avoid", text: "Не принимай важных решений — отложи до завтра" })
  } else if (mercuryRx) {
    advice.push({ sphere: "Решения", icon: "🎯", verdict: "caution", text: "Запиши решение — перечитай через 2 дня, потом действуй" })
  } else if (moonStrong && moon.isWaxing) {
    advice.push({ sphere: "Решения", icon: "🎯", verdict: "good", text: "Решения даются легко — интуиция работает чётко" })
  } else if (dayStatus === "tense") {
    advice.push({ sphere: "Решения", icon: "🎯", verdict: "caution", text: "Не решай на эмоциях — остынь, потом выбирай" })
  } else {
    advice.push({ sphere: "Решения", icon: "🎯", verdict: "neutral", text: "Обычная ясность — решения принимаются ровно" })
  }

  // 9. Поездки
  if (jupiterStrong && !voc.isVoid) {
    advice.push({ sphere: "Поездки", icon: "✈️", verdict: "good", text: "Дорога будет лёгкой — хороший день для отправления" })
  } else if (mercuryRx) {
    advice.push({ sphere: "Поездки", icon: "✈️", verdict: "caution", text: "Задержки вероятны — закладывай время на форс-мажор" })
  } else if (voc.isVoid) {
    advice.push({ sphere: "Поездки", icon: "✈️", verdict: "caution", text: "Поездки по необходимости — не планируй новое" })
  } else {
    advice.push({ sphere: "Поездки", icon: "✈️", verdict: "neutral", text: "Обычный день в дороге — без приключений" })
  }

  // 10. Творчество
  if (venusStrong && !venusRx) {
    advice.push({ sphere: "Творчество", icon: "🎨", verdict: "good", text: pick(["Вдохновение бьёт ключом — садись за работу", "Хороший день для творчества — всё удаётся"], seed + 5) })
  } else if (moonStrong && moon.isWaxing) {
    advice.push({ sphere: "Творчество", icon: "🎨", verdict: "good", text: "Эмоции питают идею — лови поток" })
  } else if (lunarDay.favorable) {
    advice.push({ sphere: "Творчество", icon: "🎨", verdict: "neutral", text: "Спокойный фон для творчества — без искр, но ровно" })
  } else {
    advice.push({ sphere: "Творчество", icon: "🎨", verdict: "caution", text: "Вдохновение спит — не форсируй, сделай заготовки" })
  }

  // 11. Учёба
  if (mercuryStrong && !mercuryRx) {
    advice.push({ sphere: "Учёба", icon: "📚", verdict: "good", text: "Память цепкая — учи сложное, оно задержится" })
  } else if (jupiterStrong) {
    advice.push({ sphere: "Учёба", icon: "📚", verdict: "good", text: "Хороший день для больших тем — смысл укладывается" })
  } else if (mercuryRx) {
    advice.push({ sphere: "Учёба", icon: "📚", verdict: "caution", text: "Повторяй старое — новое плохо усваивается" })
  } else {
    advice.push({ sphere: "Учёба", icon: "📚", verdict: "neutral", text: "Обычный темп — учи понемногу, без рывков" })
  }

  // 12. Покупки
  if (venusStrong && !venusRx) {
    advice.push({ sphere: "Покупки", icon: "🛍️", verdict: "good", text: "Вкус работает — выберешь правильное, не пожалеешь" })
  } else if (mercuryRx) {
    advice.push({ sphere: "Покупки", icon: "🛍️", verdict: "caution", text: "Не покупай электронику и технику — могут быть дефекты" })
  } else if (voc.isVoid) {
    advice.push({ sphere: "Покупки", icon: "🛍️", verdict: "caution", text: "Только необходимое — крупные покупки разочаруют" })
  } else {
    advice.push({ sphere: "Покупки", icon: "🛍️", verdict: "neutral", text: "Обычный день — покупай что нужно, без импульсов" })
  }

  return advice
}

const VERDICT_META: Record<Verdict, { label: string; color: string; bg: string }> = {
  good: { label: "да", color: "oklch(0.65 0.13 145)", bg: "oklch(0.65 0.13 145 / 0.08)" },
  caution: { label: "осторожно", color: "oklch(0.70 0.13 85)", bg: "oklch(0.70 0.13 85 / 0.08)" },
  avoid: { label: "нет", color: "oklch(0.58 0.14 27)", bg: "oklch(0.58 0.14 27 / 0.08)" },
  neutral: { label: "ровно", color: "oklch(0.55 0.06 295)", bg: "oklch(0.55 0.06 295 / 0.05)" },
}

export function ConcreteDayAdvice({ date, dayStatus, energyItems }: ConcreteDayAdviceProps) {
  const [expanded, setExpanded] = useState(false)

  const advice = useMemo(
    () => generateAdvice(date, dayStatus, energyItems),
    [date, dayStatus, energyItems],
  )

  const goodCount = advice.filter((a) => a.verdict === "good").length
  const avoidCount = advice.filter((a) => a.verdict === "avoid" || a.verdict === "caution").length

  return (
    <section className="px-6" aria-label="Конкретно по сферам">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <Zap className="h-3 w-3" strokeWidth={1.8} />
          Конкретно сегодня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        {/* Summary header */}
        <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
          <div className="flex items-center gap-3 text-[11px]">
            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {goodCount} благоприятно
            </span>
            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              {avoidCount} осторожно
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-0.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? "свернуть" : "все 12 сфер"}
            <ChevronDown
              className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
              strokeWidth={2}
            />
          </button>
        </div>

        {/* Advice list */}
        <div className="divide-y divide-border/30">
          {advice.map((a, i) => {
            const meta = VERDICT_META[a.verdict]
            const showInCompact = i < 6
            if (!expanded && !showInCompact) return null
            return (
              <motion.div
                key={a.sphere}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.04 }}
                className="flex items-start gap-2.5 px-4 py-2.5"
                style={{ background: expanded ? meta.bg : undefined }}
              >
                <span className="mt-0.5 text-[14px] leading-none flex-none">{a.icon}</span>
                <span className="w-[68px] flex-none text-[11px] font-medium text-muted-foreground">
                  {a.sphere}
                </span>
                <span className="flex-1 text-[12.5px] leading-snug text-foreground">
                  {a.text}
                </span>
                <span
                  className="mt-1 h-1.5 w-1.5 flex-none rounded-full"
                  style={{ background: meta.color }}
                  title={meta.label}
                  aria-hidden
                />
              </motion.div>
            )
          })}
        </div>

        {/* Expand hint when collapsed */}
        {!expanded && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="w-full py-2 text-center text-[11px] text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
          >
            Показать ещё {advice.length - 6} сфер ▾
          </button>
        )}
      </div>
    </section>
  )
}
