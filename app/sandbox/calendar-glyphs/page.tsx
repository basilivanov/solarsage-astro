// ############################################################################
// AI_HEADER: MODULE_SANDBOX_CALENDAR_GLYPHS — prototype variants for calendar day markers.
// ROLE: Renders three glyph variants for calendar day cells on fabricated week rows.
// ############################################################################

// START_MODULE_CONTRACT: M-SANDBOX-CALENDAR-GLYPHS
// purpose: Present candidate calendar day glyphs (A/B/C) for owner approval before implementation.
// owns:
//   - app/sandbox/calendar-glyphs/page.tsx
// inputs: none (static fabricated week data).
// outputs: three labeled variant sections with calendar-like day cells.
// dependencies: cn util only.
// side_effects: none.
// emitted_logs: none.
// invariants: prototype only; no production component changes.
// failure_policy: none.
// END_MODULE_CONTRACT: M-SANDBOX-CALENDAR-GLYPHS

// START_MODULE_MAP: M-SANDBOX-CALENDAR-GLYPHS
// public_entrypoints:
//   - CalendarGlyphsPage
// semantic_blocks:
//   - VARIANTS: three marker treatments on identical day cells.
// owned_tests:
//   - none (dev tooling)
// END_MODULE_MAP: M-SANDBOX-CALENDAR_GLYPHS

type DayMood = "supportive" | "tense" | "mixed" | "steady" | "none";

const WEEK: { day: number; mood: DayMood; today?: boolean; hero?: boolean; off?: boolean }[] = [
  { day: 27, mood: "none", off: true },
  { day: 28, mood: "none", off: true },
  { day: 29, mood: "none", off: true },
  { day: 30, mood: "none", off: true },
  { day: 31, mood: "steady" },
  { day: 1, mood: "tense", hero: true },
  { day: 2, mood: "supportive" },
];

const WEEK2: { day: number; mood: DayMood; today?: boolean }[] = [
  { day: 3, mood: "mixed", today: true },
  { day: 4, mood: "steady" },
  { day: 5, mood: "none" },
  { day: 6, mood: "supportive" },
  { day: 7, mood: "tense" },
  { day: 8, mood: "none" },
  { day: 9, mood: "mixed" },
];

function cellBase(off?: boolean, today?: boolean): string {
  return [
    "relative flex h-12 w-12 flex-col items-center justify-center rounded-full transition-colors",
    off ? "opacity-30" : "",
    today ? "ring-1 ring-border" : "",
  ].join(" ");
}

// Variant A — аспектный глиф: гармония/напряжение/смешанно геометрией (треугольник/квадрат/полукруг)
function GlyphA({ mood }: { mood: DayMood }) {
  if (mood === "none") return null;
  if (mood === "steady") return <span className="mt-0.5 h-1 w-1 rounded-full bg-foreground/25" aria-hidden />;
  const color = mood === "tense" ? "text-[#6f4a12]" : mood === "supportive" ? "text-[#285a47]" : "text-foreground/60";
  return (
    <svg viewBox="0 0 12 12" className={`mt-0.5 h-3 w-3 ${color}`} aria-hidden fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
      {mood === "supportive" ? <path d="M6 2.2 10 9.5H2Z" /> : null}
      {mood === "tense" ? <path d="M2.8 2.8h6.4v6.4H2.8Z" /> : null}
      {mood === "mixed" ? <path d="M6 1.8a4.2 4.2 0 0 1 0 8.4Z" fill="currentColor" stroke="none" /> : null}
    </svg>
  );
}

// Variant B — мини-бары «структура дня»: 1–3 столбика силы, цвет по характеру
function GlyphB({ mood }: { mood: DayMood }) {
  if (mood === "none") return null;
  const bars = mood === "steady" ? 1 : mood === "mixed" ? 2 : 3;
  const cls = mood === "tense" ? "bg-[#b07b36]" : mood === "supportive" ? "bg-[#43806d]" : "bg-foreground/45";
  return (
    <span className="mt-1 flex items-end gap-[2px]" aria-hidden>
      {Array.from({ length: bars }).map((_, i) => (
        <span key={i} className={`w-[3px] rounded-full ${cls}`} style={{ height: `${4 + i * 2.5}px` }} />
      ))}
    </span>
  );
}

// Variant C — точка-индикатор с мягким цветом + кольцо у hero
function GlyphC({ mood, hero }: { mood: DayMood; hero?: boolean }) {
  if (mood === "none") return null;
  const cls =
    mood === "tense" ? "bg-[#b07b36]" :
    mood === "supportive" ? "bg-[#43806d]" :
    mood === "mixed" ? "bg-foreground/55" : "bg-foreground/25";
  return (
    <span className="relative mt-0.5 flex items-center justify-center" aria-hidden>
      {hero ? <span className="absolute h-3 w-3 rounded-full border border-foreground/50" /> : null}
      <span className={`h-1.5 w-1.5 rounded-full ${cls}`} />
    </span>
  );
}

function Row({ variant, week }: { variant: "A" | "B" | "C"; week: typeof WEEK }) {
  return (
    <div className="flex justify-center gap-1">
      {week.map((d) => (
        <button key={`${variant}-${d.day}`} type="button" className={cellBase(d.off, d.today)}>
          <span className="font-serif text-[15px] leading-none text-foreground/85">{d.day}</span>
          {variant === "A" ? <GlyphA mood={d.mood} /> : null}
          {variant === "B" ? <GlyphB mood={d.mood} /> : null}
          {variant === "C" ? <GlyphC mood={d.mood} hero={d.hero} /> : null}
        </button>
      ))}
    </div>
  );
}

export default function CalendarGlyphsPage() {
  const sections: { id: "A" | "B" | "C"; title: string; note: string }[] = [
    { id: "A", title: "A — аспектные глифы", note: "△ гармония · □ напряжение · ◐ смешанно · точка — ровный день. Схематично, «астрологично»." },
    { id: "B", title: "B — мини-бары силы дня", note: "1–3 столбика = насыщенность; цвет = характер. Читается как «насколько день заряжен»." },
    { id: "C", title: "C — цветные точки + кольцо hero", note: "Самый тихий вариант: точка характера, кольцо вокруг неё у hero-дня." },
  ];
  return (
    <main className="mx-auto w-full max-w-md px-5 py-8">
      <h1 className="font-serif text-[24px] leading-[30px]">Иконки дня — варианты</h1>
      <p className="mt-2 text-[13px] leading-5 text-muted-foreground">
        Одна и та же неделя в трёх обработках. Цвета сдержанные: зелёный — поддержка, янтарный — напряжение, ink — смешанно/ровно.
      </p>
      {sections.map((s) => (
        <section key={s.id} className="mt-8">
          <h2 className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">{s.title}</h2>
          <p className="mt-1 text-[12px] leading-4 text-muted-foreground">{s.note}</p>
          <div className="mt-3 rounded-[24px] border border-border/40 bg-card p-4 shadow-(--shadow-card)">
            <Row variant={s.id} week={WEEK} />
            <div className="mt-1"><Row variant={s.id} week={WEEK2} /></div>
          </div>
        </section>
      ))}
    </main>
  );
}
