// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_LIST_HERO
// ROLE: Hero section component for synastry list screen
// DEPENDENCIES: react, lucide-react
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-LIST-HERO
// purpose: Render prominent product hero for synastry list screen with headline, lead text, and full-width CTA.
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

import { Plus } from "lucide-react"

type Props = {
  onAddClick: () => void
}

// START_BLOCK: SYNASTRY_LIST_HERO
export function SynastryListHero({ onAddClick }: Props) {
  return (
    <section className="space-y-4 pt-2 pb-1" data-testid="synastry-list-hero">
      <div className="space-y-1.5">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          СИНАСТРИЯ
        </span>
        <h1 className="font-serif text-[38px] sm:text-[40px] font-normal leading-[1.02] tracking-tight text-foreground">
          Кто тебе<br />подходит?
        </h1>
      </div>

      <p className="text-[14px] leading-relaxed text-muted-foreground max-w-[42ch]">
        Сначала — понятный вывод. Внутри каждого сравнения — полное астрологическое «мясо»: аспекты, орбисы, наложение домов и человеческий перевод.
      </p>

      <button
        type="button"
        onClick={onAddClick}
        data-testid="synastry-add-btn"
        className="w-full h-[52px] rounded-[17px] bg-primary text-primary-foreground font-semibold text-[15px] flex items-center justify-center gap-2 transition active:scale-[0.99] shadow-sm hover:opacity-95"
      >
        <Plus className="h-5 w-5" strokeWidth={2.2} />
        Добавить человека
      </button>
    </section>
  )
}
// END_BLOCK: SYNASTRY_LIST_HERO
