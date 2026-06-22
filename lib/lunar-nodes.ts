// ############################################################################
// AI_HEADER: MODULE_LIB_LUNAR_NODES
// ROLE: Lunar node (Rahu/Ketu, North/South Node) position computation.
// DEPENDENCIES: none
// ############################################################################

/**
 * Lunar Nodes (North/South, Rahu/Ketu) — the points where the Moon's
 * orbit crosses the ecliptic. In Vedic astrology Rahu (North Node)
 * represents destiny/desire, Ketu (South Node) represents past karma
 * /liberation. In Western astrology they're called the Dragon's Head
 * and Tail.
 *
 * The nodes move retrograde (against the zodiac direction) through
 * all 12 signs in ~18.6 years, spending ~1.5 years per sign.
 *
 * This is a simplified mean-node computation. True node positions
 * would come from the SolarSage sidecar with Swiss Ephemeris.
 */

export interface LunarNodeInfo {
  /** North node (Rahu) sign index 0-11 (Aries=0..Pisces=11) */
  northNodeSign: number
  /** North node Russian sign name */
  northNodeSignRu: string
  /** North node symbol */
  northNodeSymbol: string
  /** South node (Ketu) sign index — always opposite the north */
  southNodeSign: number
  /** South node Russian sign name */
  southNodeSignRu: string
  /** South node symbol */
  southNodeSymbol: string
  /** House where the north node falls in the user's natal chart (1-12) */
  northNodeHouse: number
  /** House where the south node falls (always opposite) */
  southNodeHouse: number
  /** Short interpretation of the north node placement */
  northNodeInterpretation: string
  /** Short interpretation of the south node placement */
  southNodeInterpretation: string
  /** Years until the nodes change sign (approximate) */
  yearsUntilSignChange: number
}

const ZODIAC = [
  { name: "Овен", symbol: "♈", element: "Огонь" },
  { name: "Телец", symbol: "♉", element: "Земля" },
  { name: "Близнецы", symbol: "♊", element: "Воздух" },
  { name: "Рак", symbol: "♋", element: "Вода" },
  { name: "Лев", symbol: "♌", element: "Огонь" },
  { name: "Дева", symbol: "♍", element: "Земля" },
  { name: "Весы", symbol: "♎", element: "Воздух" },
  { name: "Скорпион", symbol: "♏", element: "Вода" },
  { name: "Стрелец", symbol: "♐", element: "Огонь" },
  { name: "Козерог", symbol: "♑", element: "Земля" },
  { name: "Водолей", symbol: "♒", element: "Воздух" },
  { name: "Рыбы", symbol: "♓", element: "Вода" },
]

// North node sign interpretations (by sign)
const NORTH_NODE_BY_SIGN: Record<string, string> = {
  "Овен": "Учись быть первопроходцем. Развивай смелость и самостоятельность. Уходи от зависимостей.",
  "Телец": "Строй опору внутри себя. Развивай терпение и ценность. Уходи от самоотдачи до истощения.",
  "Близнецы": "Учись слушать и говорить. Развивай любопытство и гибкость. Уходи от догм.",
  "Рак": "Создавай свой дом и семью. Развивай эмоциональную глубину. Уходи от чрезмерной холодности.",
  "Лев": "Проявляй себя творчески. Развивай лидерство и щедрость. Уходи от растворения в толпе.",
  "Дева": "Наведи порядок в жизни. Развивай служение и здоровье. Уходи от хаоса и мечтаний.",
  "Весы": "Учись партнёрству. Развивай справедливость и гармонию. Уходи от воинственности.",
  "Скорпион": "Иди в глубину. Развивай трансформацию и власть. Уходи от поверхностного комфорта.",
  "Стрелец": "Ищи смысл и истину. Развивай мудрость и свободу. Уходи от мелочности.",
  "Козерог": "Бери ответственность. Развивай дисциплину и структуру. Уходи от эмоциональной зависимости.",
  "Водолей": "Будь собой. Развивай оригинальность и сообщество. Уходи от конформизма.",
  "Рыбы": "Откройся духовному. Развивай сострадание и интуицию. Уходи от чрезмерной критичности.",
}

const SOUTH_NODE_BY_SIGN: Record<string, string> = {
  "Овен": "Прошлый опыт: независимость и импульсивность. Не возвращайся к эгоизму.",
  "Телец": "Прошлый опыт: стабильность и накопление. Не цепляйся за материальное.",
  "Близнецы": "Прошлый опыт: информация и общение. Не рассеивайся.",
  "Рак": "Прошлый опыт: семья и эмоции. Не прячься в прошлом.",
  "Лев": "Прошлый опыт: признание и творчество. Не жди восхищения.",
  "Дева": "Прошлый опыт: порядок и критика. Не впадай в перфекционизм.",
  "Весы": "Прошлый опыт: партнёрство и компромисс. Не теряй себя в другом.",
  "Скорпион": "Прошлый опыт: власть и интенсивность. Не цепляйся за контроль.",
  "Стрелец": "Прошлый опыт: свобода и учительство. Не уходи в абстракции.",
  "Козерог": "Прошлый опыт: статус и контроль. Не подавляй чувства.",
  "Водолей": "Прошлый опыт: отчуждение и оригинальность. Не уходи от близости.",
  "Рыбы": "Прошлый опыт: духовность и иллюзии. Не избегай реальности.",
}

// Natal house cusps from DEMO_NATAL_RESPONSE (sign → house mapping)
// House 1 cusp at 181.24° (Libra), House 7 cusp at 1.24° (Aries), etc.
const NATAL_HOUSE_CUSPS = [
  181.24, 211.01, 236.56, 259.65, 299.47, 334.67,
  1.24, 31.01, 56.56, 79.65, 119.47, 154.67,
]

// Mean node: 18.6-year cycle, moves retrograde. Reference: 2024-01-01 = ~18° Aries.
const NODE_CYCLE_YEARS = 18.6
const REF_EPOCH = Date.UTC(2024, 0, 1)
const REF_NODE_LONGITUDE = 18 // ~18° Aries at 2024-01-01

/**
 * Compute the lunar node positions for a given date.
 */
export function getLunarNodes(date: Date): LunarNodeInfo {
  const yearsSinceEpoch = (date.getTime() - REF_EPOCH) / (365.25 * 86400000)
  // Node moves retrograde (longitude decreases)
  let northLong = (REF_NODE_LONGITUDE - yearsSinceEpoch * (360 / NODE_CYCLE_YEARS)) % 360
  if (northLong < 0) northLong += 360

  const northSign = Math.floor(northLong / 30)
  const southSign = (northSign + 6) % 12

  // Find which natal house the north node falls in
  let northHouse = 1
  for (let h = 0; h < 12; h++) {
    const cusp = NATAL_HOUSE_CUSPS[h]
    const nextCusp = NATAL_HOUSE_CUSPS[(h + 1) % 12]
    if (nextCusp > cusp) {
      if (northLong >= cusp && northLong < nextCusp) {
        northHouse = h + 1
        break
      }
    } else {
      // Wraps around 0°
      if (northLong >= cusp || northLong < nextCusp) {
        northHouse = h + 1
        break
      }
    }
  }
  const southHouse = ((northHouse + 5) % 12) + 1

  // Years until sign change: how long until northLong crosses the next 30° boundary
  const longInSign = northLong % 30
  const degreesToNextSign = 30 - longInSign
  const yearsUntilSignChange = (degreesToNextSign / 360) * NODE_CYCLE_YEARS

  const northZodiac = ZODIAC[northSign]
  const southZodiac = ZODIAC[southSign]

  return {
    northNodeSign: northSign,
    northNodeSignRu: northZodiac.name,
    northNodeSymbol: "☊",
    southNodeSign: southSign,
    southNodeSignRu: southZodiac.name,
    southNodeSymbol: "☋",
    northNodeHouse: northHouse,
    southNodeHouse: southHouse,
    northNodeInterpretation: NORTH_NODE_BY_SIGN[northZodiac.name] ?? "",
    southNodeInterpretation: SOUTH_NODE_BY_SIGN[southZodiac.name] ?? "",
    yearsUntilSignChange: Math.round(yearsUntilSignChange * 10) / 10,
  }
}
