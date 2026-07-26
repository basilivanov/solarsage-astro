// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_LIST_HERO
// ROLE: Hero section component for synastry list screen
// DEPENDENCIES: react, lucide-react
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-LIST-HERO
// purpose: Render prominent product hero for synastry list screen with topbar, headline, lead text, and full-width CTA.
// owns:
//   - components/synastry/synastry-list-hero.tsx
// inputs: onAddClick
// outputs: SynastryListHero TSX render
// dependencies: none
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-LIST-HERO

// START_MODULE_MAP: M-SYNASTRY-LIST-HERO
// public_entrypoints:
//   - SynastryListHero
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-LIST-HERO

"use client"

type Props = {
  onAddClick: () => void
}

// START_BLOCK: SYNASTRY_LIST_HERO
export function SynastryListHero({ onAddClick }: Props) {
  return (
    <div className="space-y-4">
      {/* Brand Topbar */}
      <header
        data-testid="synastry-brand-topbar"
        className="flex h-[58px] items-center justify-between pt-[max(10px,env(safe-area-inset-top))] px-4"
      >
        <div className="flex items-center gap-2 text-[12px] font-extrabold uppercase tracking-[0.13em] text-[#3e3347] dark:text-[#f1e9f4]">
          <span className="flex h-[25px] w-[25px] items-center justify-center rounded-full bg-[#795a86] text-white text-[13px]">
            ✦
          </span>
          Solar Sage
        </div>

        <button
          type="button"
          disabled
          aria-disabled="true"
          aria-label="О синастрии"
          className="flex h-[44px] w-[44px] items-center justify-center rounded-[15px] border border-[#795a86]/16 bg-[#fffdf9]/78 dark:bg-[#2d2233]/78 text-[#3e3347] dark:text-[#f1e9f4] font-serif text-[15px] cursor-not-allowed opacity-80"
        >
          i
        </button>
      </header>

      {/* Hero Section */}
      <section className="px-4 space-y-4" data-testid="synastry-list-hero">
        <div>
          <p className="mb-2 text-[11px] font-extrabold uppercase tracking-[0.12em] text-[#795a86]">
            СИНАСТРИЯ
          </p>
          <h1 className="syn-serif text-[40px] font-medium leading-[0.98] tracking-[-0.035em] mb-3.5 text-[#3e3347] dark:text-[#f1e9f4]">
            Кто тебе<br />подходит?
          </h1>
        </div>

        <p className="text-[15px] leading-[1.55] text-[#7d7284] dark:text-muted-foreground mb-5">
          Сначала — понятный вывод. Внутри каждого сравнения — полное астрологическое «мясо»: аспекты, орбисы, наложение домов и человеческий перевод.
        </p>

        <button
          type="button"
          onClick={onAddClick}
          data-testid="synastry-add-btn"
          className="w-full rounded-[17px] bg-[#795a86] text-white px-[18px] py-[15px] text-[16px] font-[760] flex items-center justify-center gap-2 transition active:scale-[0.99] shadow-none hover:opacity-95"
        >
          ＋ Добавить человека
        </button>
      </section>
    </div>
  )
}
// END_BLOCK: SYNASTRY_LIST_HERO
