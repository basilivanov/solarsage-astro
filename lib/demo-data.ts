
// ############################################################################
// AI_HEADER: MODULE_LIB_DEMO_DATA
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/demo-data.ts
// owns:
//   - lib/demo-data.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

/**
 * Демо-данные для всех экранов приложения.
 * Используются когда NEXT_PUBLIC_DEMO_MODE=true (для v0.app и локальной разработки без API).
 *
 * Данные основаны на реальном API-ответе (2026-06-02, Москва, 55.75/37.62).
 */

// ── День (Today) ───────────────────────────────────────────────────

export const DEMO_TODAY_RESPONSE = {
  meta: {
    schemaVersion: "today/v1",
    contractVersion: 2,
    calculationVersion: 1,
    normalizationVersion: 1,
    scoringVersion: 1,
    promptVersion: 1,
    contentVersion: 1,
    generatedAt: "2026-06-02T12:00:00Z",
    cached: false,
  },
  date: "2026-06-02",
  title: "Сегодня",
  headline: "Сегодня день устойчивый — опирайся на рутину, но будь внимателен к деталям в общении.",
  dayStatus: "steady",
  access: { state: "full" },
  topFlags: [
    { iconName: "Sun-opposition", title: "Солнце напротив Марса", summary: "Орб: 0.5°, сила: 0.94" },
    { iconName: "Moon-sextile", title: "Луна в секстиле с Меркурием", summary: "Орб: 1.6°, сила: 0.73" },
    { iconName: "Mercury-square", title: "Меркурий в квадратуре с Сатурном", summary: "Орб: 1.4°, сила: 0.80" },
  ],
  reading: {
    paragraphs: [
      "Сегодня будет довольно стабильный день, но в то же время в нём ощутятся мощные энергии, которые стоит использовать. С одной стороны, оппозиция между Солнцем и Марсом может создавать небольшие препятствия или конфликты, особенно в сфере личной инициативы. Будь внимателен к своему настроению и старайся избегать излишней агрессии в общении. Лучше направить эту энергию на физическую активность: занятия спортом или какие-то проекты, где требуется решительность.",
      "Неплохое влияние Луны добавляет больше чувствительности и эмоциональности в сегодняшний день. Луна в секстиле с Меркурием располагает к тому, чтобы разбираться в своих чувствах, обсуждать насущные темы с близкими или просто уделить время полезному чтению — это отличная возможность для установления более тёплого контакта с окружающими.",
      "Вечером обрати внимание на домашние дела и личные пространства: квадратура Меркурия с Сатурном может привести к задержкам в коммуникации или мелким недоразумениям. Постарайся планировать важные разговоры на вторую половину дня, когда эмоциональный фон будет менее напряжённым.",
    ],
  },
  whyThisHappens: {
    sections: [
      {
        id: "why-1", title: "Главная тема дня",
        blocks: [{ kind: "paragraph", text: "Сегодня день вызовов и возможностей: оппозиция Солнца и Марса (сила 0.94) создаёт фоновую напряжённость, но секстиль Луны с Меркурием (0.73) даёт шанс разобраться в чувствах." }],
      },
      {
        id: "why-2", title: "Быстрый слой дня",
        blocks: [{ kind: "paragraph", text: "Луна в Козероге (18°) проходит через твой 6 дом работы и здоровья. Она в квадратуре с натальным Сатурном в Весах — это создаёт трение в личных делах и коммуникациях." }],
      },
      {
        id: "why-3", title: "Почему это задевает именно тебя",
        blocks: [{ kind: "paragraph", text: "Сегодня Венера — планета любви и удовольствий — соединяется с твоим Юпитером (0.2°), планетой роста и удачи, в Весах, в твоём 3 доме общения. Это делает день особенно важным для контактов и социальных связей." }],
      },
      {
        id: "why-4", title: "Фон периода",
        blocks: [{ kind: "paragraph", text: "Фон дня строится по длительным транзитам, сосредоточенным на личных и семейных вопросах (4 дом) и личной самореализации (1 дом). Это время для рефлексии и оценки эмоциональной базы." }],
      },
      {
        id: "why-5", title: "Что усиливает этот день",
        blocks: [{ kind: "paragraph", text: "Солнце в оппозиции (противостояние, нужен баланс) с твоим Марсом (орб 0.5°, сила 0.94). Это создаёт напряжение — реакции острее, конфликты вероятнее. Квадратура Луны с Сатурном (0.6°, сила 0.92) добавляет ощущение тяжести и ответственности." }],
      },
      {
        id: "why-6", title: "Что смягчает этот день",
        blocks: [{ kind: "paragraph", text: "Луна в секстиле (мягкая возможность, нужно приложить усилие) с Меркурием (орб 1.6°, сила 0.73). Это даёт шанс на понимание и тёплый контакт. Плутон в трине с Сатурном (0.6°, сила 0.92) помогает находить неожиданные решения." }],
      },
      {
        id: "why-7", title: "Через какие сферы это проявляется",
        blocks: [{ kind: "paragraph", text: "Активированы 10 дом (карьера, статус, репутация), 6 дом (работа, здоровье, порядок) и 3 дом (общение, учёба, ближний круг). Эти сферы сегодня требуют внимания и взаимодействия." }],
      },
      {
        id: "why-8", title: "Астрологический смысл дня",
        blocks: [{ kind: "paragraph", text: "Сегодня ты сталкиваешься с вызовами в отношениях и самовыражении. Важно уделить внимание внутренним эмоциям и запросам, особенно с учётом квадратур и соединений." }],
      },
      {
        id: "why-9", title: "Что это значит практически",
        blocks: [{ kind: "bullets", items: ["Сфокусируйся на рутине, избегай конфликтов", "Дай себе паузу перед реакцией — эмоции могут зашкаливать", "Ищи возможности для гармонизации через общение", "Не принимай резких решений — перепроверь договорённости"] }],
      },
    ],
  },
  weekStrip: [
    { date: "2026-05-30", dayStatus: "steady", isToday: false },
    { date: "2026-05-31", dayStatus: "steady", isToday: false },
    { date: "2026-06-01", dayStatus: "supportive", isToday: false },
    { date: "2026-06-02", dayStatus: "steady", isToday: true },
    { date: "2026-06-03", dayStatus: "tense", isToday: false },
    { date: "2026-06-04", dayStatus: "steady", isToday: false },
    { date: "2026-06-05", dayStatus: "supportive", isToday: false },
  ],
  importantToday: [
    {
      id: "full_moon_window",
      type: "full_moon_window",
      title: "Полнолуние ещё ощущается",
      subtitle: "Эмоции и важные темы проявляются ярче",
      severity: "info",
      priority: 82,
      source: "live_calculation",
      details: {
        meaning: "Полнолуние усиливает эмоциональную реакцию на события, позволяя осознать важные для вас темы.",
        whyImportant: "То, что раньше было фоном, может выйти наружу и потребовать реакции.",
        personalContext: "Дом полнолуния показывает сферу, где проще увидеть результат, напряжение или необходимость завершения.",
      },
    },
    {
      id: "exact_daily_aspect",
      type: "exact_daily_aspect",
      title: "Солнце в оппозиции с Марс",
      subtitle: "Напряжение между темами — ищи баланс, а не крайность",
      severity: "soft_warning",
      priority: 70,
      source: "live_calculation",
      details: {
        meaning: "Оппозиция между Солнцем и Марсом говорит о напряжении и конфликтах, которые могут вспыхнуть на пустом месте.",
        whyImportant: "Энергия дня направлена вовне — важно не вступать в ненужные споры.",
        personalContext: "Этот аспект затрагивает твой 1 и 7 дом — темы личности и партнёрства.",
      },
    },
    {
      id: "active_house",
      type: "active_house",
      title: "Активен 10 дом",
      subtitle: "Рабочие темы и ответственность ощущаются сильнее",
      severity: "info",
      house: 10,
      priority: 50,
      source: "live_calculation",
      details: {
        meaning: "Активный 10 дом подчеркивает важность карьерных вопросов и общественного статуса.",
        whyImportant: "Даже небольшие события в этой зоне могут ощущаться заметнее обычного.",
        personalContext: "Сегодня главные сигналы собираются вокруг этой сферы, поэтому лучше дать ей внимание и не распыляться.",
      },
    },
  ],
  notes: "Сегодня важное влияние на отношения и партнёрство, так что постарайся уделить внимание близким. Это удачное время для того, чтобы направить свою энергию в русло самовыражения.",
}

// ── Календарь (Calendar) ───────────────────────────────────────────

export const DEMO_CALENDAR_RESPONSE = {
  month: "2026-06",
  days: Array.from({ length: 30 }, (_, i) => ({
    date: `2026-06-${String(i + 1).padStart(2, "0")}`,
    dayStatus: (["supportive", "steady", "tense"] as const)[i % 3],
    isAvailable: i <= 15, // first 15 days available, rest locked
  })),
}

// ── Доступ (Access) ────────────────────────────────────────────────

export const DEMO_ACCESS = {
  state: "trial" as const,
  hasAccess: true,
  accessStart: null,
  accessEnd: null,
  daysLeft: 14,
}

// ── Профиль (Profile) ──────────────────────────────────────────────

export const DEMO_PROFILE = {
  birthday: "1990-01-15",
  birthTime: "12:00",
  birthLat: 55.75,
  birthLon: 37.62,
  birthTz: "Europe/Moscow",
}

// ── Натальная карта (Natal) ────────────────────────────────────────

export const DEMO_NATAL_RESPONSE = {
  planets: [
    { name: "Sun", sign: "Capricorn", longitude: 294.5, house: 4 },
    { name: "Moon", sign: "Leo", longitude: 129.1, house: 11 },
    { name: "Mercury", sign: "Sagittarius", longitude: 267.6, house: 3 },
    { name: "Venus", sign: "Aquarius", longitude: 310.7, house: 5 },
    { name: "Mars", sign: "Sagittarius", longitude: 253.4, house: 3 },
    { name: "Jupiter", sign: "Cancer", longitude: 94.3, house: 10 },
    { name: "Saturn", sign: "Capricorn", longitude: 289.0, house: 4 },
    { name: "Uranus", sign: "Capricorn", longitude: 285.2, house: 4 },
    { name: "Neptune", sign: "Capricorn", longitude: 281.6, house: 4 },
    { name: "Pluto", sign: "Scorpio", longitude: 222.3, house: 2 },
  ],
  houses: [
    { number: 1, cusp: 181.24, sign: "Libra" },
    { number: 2, cusp: 211.01, sign: "Scorpio" },
    { number: 3, cusp: 236.56, sign: "Scorpio" },
    { number: 4, cusp: 259.65, sign: "Sagittarius" },
    { number: 5, cusp: 299.47, sign: "Capricorn" },
    { number: 6, cusp: 334.67, sign: "Pisces" },
    { number: 7, cusp: 1.24, sign: "Aries" },
    { number: 8, cusp: 31.01, sign: "Taurus" },
    { number: 9, cusp: 56.56, sign: "Taurus" },
    { number: 10, cusp: 79.65, sign: "Gemini" },
    { number: 11, cusp: 119.47, sign: "Cancer" },
    { number: 12, cusp: 154.67, sign: "Virgo" },
  ],
  houseSystem: "PLACIDUS",
}

// ── Список городов (Geo/Cities) ────────────────────────────────────

export const DEMO_CITIES = [
  { name: "Москва", lat: 55.75, lon: 37.62, country: "Россия", timezone: "Europe/Moscow" },
  { name: "Санкт-Петербург", lat: 59.93, lon: 30.34, country: "Россия", timezone: "Europe/Moscow" },
  { name: "Новосибирск", lat: 55.02, lon: 82.93, country: "Россия", timezone: "Asia/Novosibirsk" },
  { name: "Екатеринбург", lat: 56.84, lon: 60.65, country: "Россия", timezone: "Asia/Yekaterinburg" },
  { name: "Казань", lat: 55.79, lon: 49.12, country: "Россия", timezone: "Europe/Moscow" },
  { name: "Лондон", lat: 51.51, lon: -0.13, country: "Великобритания", timezone: "Europe/London" },
  { name: "Нью-Йорк", lat: 40.71, lon: -74.01, country: "США", timezone: "America/New_York" },
]

// ── Хорар (Horary) ──────────────────────────────────────────────────

export const DEMO_HORARY_QUOTA = {
  weeklyFreeAvailable: true,
  weeklyFreeExpiresAt: "2026-06-09T00:00:00Z",
  nextWeeklyFreeAt: "2026-06-09T00:00:00Z",
  bonusCredits: 2,
  paidCredits: 3,
  canPurchase: true,
}

export const DEMO_HORARY_QUESTIONS = [
  // ── 1. Отвеченный: «Да» (любовь) ────────────────────────────────
  {
    id: "hq-love-yes-001",
    text: "Выйду ли я замуж в этом году?",
    category: "love" as const,
    status: "answered" as const,
    spentCreditSource: "subscription_weekly_free" as const,
    creditRefunded: false,
    clientTimezone: "Europe/Moscow",
    clientLocalTime: "2026-06-01T14:30:00",
    questionLocationName: "Москва",
    createdAt: "2026-06-01T14:30:00Z",
    answer: {
      verdict: "yes" as const,
      confidence: 0.78,
      confidenceLabel: "high" as const,
      confidenceExplanation: "Карта указывает на позитивный исход с высокой уверенностью. Аспекты между управителями 1 и 7 домов поддерживают союз.",
      blocks: [
        {
          type: "verdict_card" as const,
          verdict: "yes" as const,
          confidence: 0.78,
          label: "Да, скорее всего",
          confidenceLabel: "high" as const,
          confidenceExplanation: "Карта указывает на позитивный исход с высокой уверенностью. Аспекты между управителями 1 и 7 домов поддерживают союз.",
        },
        { type: "divider" as const },
        {
          type: "heading" as const,
          text: "Разбор карты",
          level: 2,
        },
        {
          type: "lead" as const,
          text: "На момент вопроса Луна находится в Тельце — знак стабильности и постоянства. Управитель 7 дома Венера в секстиле с Юпитером — это сильный показатель благоприятного союза.",
        },
        {
          type: "testimonies" as const,
          prosLabel: "Свидетельства «за»",
          consLabel: "Свидетельства «против»",
          neutralLabel: "Нейтральные факторы",
          pros: [
            { title: "Венера в секстиле с Юпитером", explanation: "Управитель 7 дома (партнёрство) в благоприятном аспекте с планетой удачи — указывает на счастливый союз", weight: 0.85, planets: ["Венера", "Юпитер"], aspectType: "sextile", orb: 1.2 },
            { title: "Луна в Тельце", explanation: "Луна в знаке экзальтации — эмоции стабильны и направлены на создание семьи", weight: 0.72, planets: ["Луна"], aspectType: null, orb: null },
            { title: "Солнце в соединении с управителем ASC", explanation: "Вопросящий в сильной позиции — готов к действию", weight: 0.65, planets: ["Солнце", "Меркурий"], aspectType: "conjunction", orb: 2.1 },
          ],
          cons: [
            { title: "Сатурн в квадратуре с Луной", explanation: "Возможны задержки из-за обстоятельств, но не отказ", weight: 0.45, planets: ["Сатурн", "Луна"], aspectType: "square", orb: 3.5 },
          ],
          neutral: [
            { title: "Марс в 3 доме", explanation: "Активные обсуждения и переписка — информация о браке может прийти через общение", weight: 0.30, planets: ["Марс"], aspectType: null, orb: null },
          ],
        },
        { type: "divider" as const },
        {
          type: "heading" as const,
          text: "Сроки",
          level: 3,
        },
        {
          type: "timing" as const,
          status: "known" as const,
          timeRange: "август — октябрь 2026",
          text: "Луна в фиксированном знаке указывает на средний срок. Активация Венеры ретроградной в сентябре может стать поворотным моментом. Наиболее вероятное окно — август–октябрь текущего года.",
        },
        {
          type: "callout" as const,
          text: "Не форсируй события — карта показывает, что естественное развитие ситуации приведёт к нужному результату. Лучшая стратегия сейчас — быть открытой и не давить.",
          title: "Совет",
          tone: "tip" as const,
        },
      ],
      planets: ["Венера", "Юпитер", "Луна", "Сатурн", "Солнце", "Меркурий", "Марс"],
      generatedAt: "2026-06-01T14:30:45Z",
    },
  },

  // ── 2. Отвеченный: «Нет» (карьера) ──────────────────────────────
  {
    id: "hq-career-no-002",
    text: "Стоит ли мне переходить на новую работу в этом месяце?",
    category: "career" as const,
    status: "answered" as const,
    spentCreditSource: "paid" as const,
    creditRefunded: false,
    clientTimezone: "Europe/Moscow",
    clientLocalTime: "2026-05-28T09:15:00",
    questionLocationName: "Москва",
    createdAt: "2026-05-28T09:15:00Z",
    answer: {
      verdict: "no" as const,
      confidence: 0.71,
      confidenceLabel: "high" as const,
      confidenceExplanation: "Управитель 10 дома в оппозиции с Марсом — конфликт интересов и переоценка ситуации. Переход сейчас несёт риски.",
      blocks: [
        {
          type: "verdict_card" as const,
          verdict: "no" as const,
          confidence: 0.71,
          label: "Нет, сейчас не стоит",
          confidenceLabel: "high" as const,
          confidenceExplanation: "Управитель 10 дома в оппозиции с Марсом — конфликт интересов и переоценка ситуации. Переход сейчас несёт риски.",
        },
        { type: "divider" as const },
        {
          type: "heading" as const,
          text: "Разбор карты",
          level: 2,
        },
        {
          type: "paragraph" as const,
          text: "На момент вопроса управитель 10 дома (карьера) Сатурн находится в оппозиции с Марсом. Это классический показатель препятствий и конфликта. Новая позиция может оказаться не такой привлекательной, как кажется на первый взгляд.",
        },
        {
          type: "testimonies" as const,
          prosLabel: "Свидетельства «за»",
          consLabel: "Свидетельства «против»",
          neutralLabel: "Нейтральные факторы",
          pros: [
            { title: "Юпитер в трине с МС", explanation: "Долгосрочные перспективы роста существуют, но они проявятся позже", weight: 0.55, planets: ["Юпитер"], aspectType: "trine", orb: 2.8 },
          ],
          cons: [
            { title: "Сатурн в оппозиции с Марсом", explanation: "Прямое указание на конфликт и препятствия при перемене места работы", weight: 0.88, planets: ["Сатурн", "Марс"], aspectType: "opposition", orb: 1.5 },
            { title: "Управитель 2 дома поражён", explanation: "Финансовые условия перехода могут быть хуже текущих", weight: 0.70, planets: ["Плутон", "Венера"], aspectType: "square", orb: 0.8 },
            { title: "Луна в 12 доме", explanation: "Скрытые обстоятельства, о которых вы не знаете — информация неполная", weight: 0.62, planets: ["Луна"], aspectType: null, orb: null },
          ],
          neutral: [
            { title: "Меркурий ретроградный", explanation: "Документы и договорённости могут пересматриваться — не спешите подписывать", weight: 0.40, planets: ["Меркурий"], aspectType: null, orb: null },
          ],
        },
        {
          type: "callout" as const,
          text: "Подожди с переходом минимум до конца ретроградного Меркурия (10 июня). Если предложение останется — пересмотри вопрос заново.",
          title: "Рекомендация",
          tone: "warning" as const,
        },
      ],
      planets: ["Сатурн", "Марс", "Плутон", "Венера", "Луна", "Меркурий", "Юпитер"],
      generatedAt: "2026-05-28T09:15:52Z",
    },
  },

  // ── 3. Отвеченный: «Может быть» (деньги) ───────────────────────
  {
    id: "hq-money-maybe-003",
    text: "Будет ли у меня доход от нового проекта?",
    category: "money" as const,
    status: "answered" as const,
    spentCreditSource: "referral_bonus" as const,
    creditRefunded: false,
    clientTimezone: "Europe/Moscow",
    clientLocalTime: "2026-05-25T18:45:00",
    questionLocationName: "Санкт-Петербург",
    createdAt: "2026-05-25T18:45:00Z",
    answer: {
      verdict: "maybe" as const,
      confidence: 0.52,
      confidenceLabel: "medium" as const,
      confidenceExplanation: "Карта не даёт однозначного ответа. Свидетельства «за» и «против» примерно равны — исход зависит от ваших действий.",
      blocks: [
        {
          type: "verdict_card" as const,
          verdict: "maybe" as const,
          confidence: 0.52,
          label: "Возможно, но не гарантировано",
          confidenceLabel: "medium" as const,
          confidenceExplanation: "Карта не даёт однозначного ответа. Свидетельства «за» и «против» примерно равны — исход зависит от ваших действий.",
        },
        { type: "divider" as const },
        {
          type: "paragraph" as const,
          text: "Управитель 2 дома (финансы) Венера не имеет мажорных аспектов — ситуация «висит». Это означает, что результат ещё не определён и сильно зависит от твоей проактивности.",
        },
        {
          type: "pros_cons" as const,
          pros: ["Юпитер во 2 доме — потенциал для дохода существует", "Венера в секстиле с Марсом — энергия для действий есть"],
          cons: ["Луна в квадратуре с Нептуном — возможна путаница в финансах", "Управитель 2 дома без аспектов — нет чёткого канала для денег"],
          prosLabel: "Что говорит за",
          consLabel: "Что говорит против",
        },
        {
          type: "timing" as const,
          status: "unclear" as const,
          timeRange: "июль — август 2026",
          text: "Сроки размыты. Юпитер во 2 доме указывает на потенциальное окно в июле–августе, но многое зависит от твоих действий в ближайшие недели.",
        },
        {
          type: "list" as const,
          style: "check" as const,
          items: [
            "Прояви инициативу — карта не сработает сама по себе",
            "Проверь все расчёты — Нептун говорит о возможных иллюзиях",
            "Не вкладывай больше, чем готов потерять",
          ],
        },
      ],
      planets: ["Венера", "Юпитер", "Марс", "Луна", "Нептун"],
      generatedAt: "2026-05-25T18:45:38Z",
    },
  },

  // ── 4. Не удалось (failed) — деньги возвращены ──────────────────
  {
    id: "hq-health-fail-004",
    text: "Пройдёт ли болезнь к концу месяца?",
    category: "health" as const,
    status: "failed" as const,
    spentCreditSource: "subscription_weekly_free" as const,
    creditRefunded: true,
    clientTimezone: "Europe/Moscow",
    clientLocalTime: "2026-05-20T11:00:00",
    questionLocationName: "Москва",
    createdAt: "2026-05-20T11:00:00Z",
    answer: null,
  },

  // ── 5. Истёк срок (expired) — деньги возвращены ─────────────────
  {
    id: "hq-travel-exp-005",
    text: "Удачным ли будет переезд в Нижний Новгород?",
    category: "travel" as const,
    status: "expired" as const,
    spentCreditSource: "paid" as const,
    creditRefunded: true,
    clientTimezone: "Europe/Moscow",
    clientLocalTime: "2026-05-15T16:20:00",
    questionLocationName: "Москва",
    createdAt: "2026-05-15T16:20:00Z",
    answer: null,
  },

  // ── 6. Отвеченный: «Да» (другое) — с точным сроком ─────────────
  {
    id: "hq-other-yes-006",
    text: "Найду ли я потерянные ключи от квартиры?",
    category: "other" as const,
    status: "answered" as const,
    spentCreditSource: "paid" as const,
    creditRefunded: false,
    clientTimezone: "Europe/Moscow",
    clientLocalTime: "2026-06-02T08:30:00",
    questionLocationName: "Москва",
    createdAt: "2026-06-02T08:30:00Z",
    answer: {
      verdict: "yes" as const,
      confidence: 0.91,
      confidenceLabel: "high" as const,
      confidenceExplanation: "Управитель 2 дома (потерянная вещь) в соединении с Луной — вещь найдётся быстро.",
      blocks: [
        {
          type: "verdict_card" as const,
          verdict: "yes" as const,
          confidence: 0.91,
          label: "Да, точно найдёшь",
          confidenceLabel: "high" as const,
          confidenceExplanation: "Управитель 2 дома (потерянная вещь) в соединении с Луной — вещь найдётся быстро.",
        },
        { type: "divider" as const },
        {
          type: "paragraph" as const,
          text: "Управитель 2 дома Меркурий находится в соединении с Луной — это классический показатель скорого обнаружения потерянной вещи. Луна в подвижном знаке Близнецов — ключи перемещались, но находятся недалеко.",
        },
        {
          type: "quote" as const,
          text: "Ищи там, где обычно хранишь мелочи — в сумке, кармане куртки или возле входной двери.",
          source: "Хорарная традиция",
        },
        {
          type: "timing" as const,
          status: "known" as const,
          timeRange: "сегодня, до вечера",
          text: "Луна быстрая и подвижная — ключи найдутся в тот же день, вероятнее всего до вечера. Обрати внимание на место, где ты обычно оставляешь мелкие предметы.",
        },
        {
          type: "callout" as const,
          text: "Не трать время на поиски в необычных местах — карта указывает, что ключи в привычном месте, просто ты их не замечаешь.",
          title: "Подсказка",
          tone: "tip" as const,
        },
      ],
      planets: ["Меркурий", "Луна"],
      generatedAt: "2026-06-02T08:30:30Z",
    },
  },

  // ── 7. В процессе (processing) ──────────────────────────────────
  {
    id: "hq-love-proc-007",
    text: "Вернётся ли ко мне бывший партнёр?",
    category: "love" as const,
    status: "processing" as const,
    spentCreditSource: "bonus" as const,
    creditRefunded: false,
    clientTimezone: "Europe/Moscow",
    clientLocalTime: "2026-06-02T12:00:00",
    questionLocationName: "Казань",
    createdAt: "2026-06-02T12:00:00Z",
    answer: null,
  },
]

// ── Натал (Preview) ────────────────────────────────────────────────

export const DEMO_NATAL_PREVIEW = {
  meta: {
    name: "Анна",
    birthDate: "1990-01-15",
    birthTime: "12:00",
    birthCity: "Москва",
    houseSystem: "PLACIDUS",
    ascSign: "Cancer",
    ascDegree: 14.2,
    gender: "female" as const,
  },
  highlights: [
    {
      id: "h-asc",
      title: "Асцендент",
      value: "Рак",
      description: "Как ты входишь в контакт с миром",
    },
    {
      id: "h-sun",
      title: "Солнце",
      value: "Козерог",
      description: "Твой базовый вектор и мотивация",
    },
    {
      id: "h-moon",
      title: "Луна",
      value: "Лев",
      description: "Твой эмоциональный отклик",
    },
  ],
  spheres: [
    { id: "s-body", title: "Тело, энергия, здоровье", score: 4.7, rank: 1, description: "Физическая витальность и ресурсы — одна из самых выраженных тем карты" },
    { id: "s-relations", title: "Отношения и партнёрство", score: 4.3, rank: 2, description: "Тема связи с другим человеком проявлена ярко и требует внимания" },
    { id: "s-money", title: "Деньги и ресурсы", score: 3.9, rank: 3, description: "Финансовая сфера активна — есть потенциал для роста" },
    { id: "s-career", title: "Карьера и реализация", score: 3.5, rank: 4, description: "Профессиональная сфера стабильна, но требует осознанного подхода" },
    { id: "s-family", title: "Семья и корни", score: 3.2, rank: 5, description: "Родовые сценарии и домашняя среда влияют на многие решения" },
    { id: "s-creative", title: "Творчество и самовыражение", score: 2.8, rank: 6, description: "Творческая энергия есть, но не всегда находит выход" },
    { id: "s-spiritual", title: "Духовный путь", score: 2.1, rank: 7, description: "Внутренний поиск и трансформация — фоновая, но важная тема" },
  ],
  planets: [
    { id: "p-venus", name: "Венера", sign: "Водолей", house: 5, score: 4.6, description: "Любовь и красота через свободу и нестандартность" },
    { id: "p-moon", name: "Луна", sign: "Лев", house: 11, score: 4.2, description: "Эмоции яркие, потребность в признании и тепле" },
    { id: "p-jupiter", name: "Юпитер", sign: "Рак", house: 10, score: 3.8, description: "Расширение через семью, заботу и профессию" },
    { id: "p-sun", name: "Солнце", sign: "Козерог", house: 4, score: 3.5, description: "Амбиции, структура, связь с корнями" },
    { id: "p-saturn", name: "Сатурн", sign: "Козерог", house: 4, score: 3.3, description: "Дисциплина и ответственность как фундамент" },
    { id: "p-mercury", name: "Меркурий", sign: "Стрелец", house: 3, score: 2.9, description: "Мышление масштабное, коммуникабельность" },
    { id: "p-mars", name: "Марс", sign: "Стрелец", house: 3, score: 2.7, description: "Энергия направлена на познание и действие" },
  ],
  chapters: [
    { id: "ch-impression", eyebrow: "Раздел 1", title: "Главное впечатление от карты", locked: true, description: "Общий портрет: ключевые темы, доминанты и центральная связка" },
    { id: "ch-asc", eyebrow: "Раздел 2", title: "Твоя базовая настройка", locked: true, description: "Асцендент — как ты входишь в жизнь и контакт с миром" },
    { id: "ch-rulers", eyebrow: "Раздел 3", title: "Управители карты", locked: true, description: "Традиционный и современный управитель — что ими движет" },
    { id: "ch-sun", eyebrow: "Раздел 4", title: "Солнце: ядро личности", locked: true, description: "Солнце в знаке и доме — твой базовый вектор и мотивация" },
    { id: "ch-stellium", eyebrow: "Раздел 5", title: "Сильный дом: стеллиум", locked: true, description: "Где скопились планеты — зона максимальной активности" },
    { id: "ch-mercury", eyebrow: "Раздел 6", title: "Меркурий: мышление и речь", locked: true, description: "Как ты мыслишь, говоришь и формулируешь" },
    { id: "ch-moon", eyebrow: "Раздел 7", title: "Луна: эмоции и внутренняя база", locked: true, description: "Луна в знаке и доме — привычные реакции и эмоциональная безопасность" },
    { id: "ch-venus-saturn", eyebrow: "Раздел 8", title: "Венера, Сатурн и Лилит", locked: true, description: "Скрытые чувства, внутренняя дисциплина и теневые сценарии" },
    { id: "ch-mars", eyebrow: "Раздел 9", title: "Марс: воля и действие", locked: true, description: "Как ты действуешь, защищаешь и проявляешься" },
    { id: "ch-money", eyebrow: "Раздел 10", title: "Деньги и ресурс", locked: true, description: "2 дом: как включается тема денег, самоценности и личной опоры" },
    { id: "ch-career", eyebrow: "Раздел 11", title: "Карьера и видимость", locked: true, description: "MC и Северный узел — направление роста и профессиональный путь" },
    { id: "ch-parses", eyebrow: "Раздел 12", title: "Дополнительные точки", locked: true, description: "Парсы, Селена, Вертекс — тонкие акценты и скрытые смыслы" },
    { id: "ch-stars", eyebrow: "Раздел 13", title: "Фиксированные звёзды и аспекты", locked: true, description: "Звёздные соединения и главные напряжённые/поддерживающие аспекты" },
  ],
  personalHook: "Ты считываешь мир глубоко и тонко. В карте заметно сочетание чувствительности, внутренней силы и выраженной личной воли. Сильнее всего у тебя читаются темы тела, ресурса и личного проявления.",
  calculationStats: {
    planetsCount: 10,
    housesCount: 12,
    aspectsCount: 24,
    spheresCount: 7,
    specialPointsCount: 3,
    scoringFactorsCount: 48,
    dignityFactorsCount: 14,
    totalFactorsCount: 111,
    displayLabel: "111+ факторов карты",
  },
  salesBullets: [
    "поймёшь, в чём у тебя больше всего силы;",
    "увидишь, какие темы в жизни для тебя приоритетны;",
    "получишь связный разбор карты, а не набор разрозненных фактов.",
  ],
  fullReportAvailable: true,
  fullReportPriceKopecks: 99900,
}

// ── Чат (Chat) ─────────────────────────────────────────────────────

export const DEMO_CHAT_MESSAGES = [
  {
    id: "msg-1",
    role: "user",
    text: "Что сегодня важно знать про отношения?",
    timestamp: "2026-06-02T10:00:00Z",
  },
  {
    id: "msg-2",
    role: "assistant",
    text: "Сегодня твоя Венера — планета любви и удовольствий — соединяется с Юпитером, планетой роста и удачи, в твоём 3 доме общения. Это значит, что деньги и симпатии могут прийти через разговор или переписку. Особенно удачны переговоры один-на-один и любые ситуации, где нужно кого-то в чём-то убедить. При этом дневная оппозиция Солнца и Марса создаёт напряжённый фон — старайся не вступать в ненужные споры.",
    timestamp: "2026-06-02T10:00:03Z",
  },
  {
    id: "msg-3",
    role: "user",
    text: "А как лучше всего провести вечер?",
    timestamp: "2026-06-02T10:01:00Z",
  },
  {
    id: "msg-4",
    role: "assistant",
    text: "Вечером Луна в Козероге активирует твой 6 дом работы и порядка — хорошее время для планирования завтрашнего дня или завершения начатых дел. Квадратура Меркурия с Сатурном может принести задержки в переписке — не жди мгновенных ответов на сообщения. Лучше проведи вечер за чтением или в спокойной обстановке с близкими.",
    timestamp: "2026-06-02T10:01:04Z",
  },
]
