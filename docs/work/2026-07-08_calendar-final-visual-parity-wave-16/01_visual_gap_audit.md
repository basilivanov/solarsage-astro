# Visual Gap Audit: 3002 Production vs 3001 Oracle

This audit evaluates the visual and interactive parity of the `/calendar` screen on production port `3002` against the mock-preview oracle on port `3001`.

## Audit Matrix

| Area | 3001 Oracle Behavior | Current 3002 Behavior | Classification | Required Fix / Action |
| :--- | :--- | :--- | :--- | :--- |
| **1. Header/buttons/month title** | Renders "Календарь" in uppercase and the Month Year in serif. Month navigation is clamp-restricted. | Renders the exact same header structure and clamped navigation. | `NO_GAP` | No code change. |
| **2. Segmented control final states & interaction** | Uses a sliding `framer-motion` layout animation for the switch transition between "Дни" and "Луна". | Uses static class-based switches with no slide animation. | `STYLE_GAP` | Re-implement the `framer-motion` `layoutId="cal-toggle"` transition inside the segmented control buttons. |
| **3. Lunar calendar top card: spacing** | Spaced cleanly above the grid. Spacing is consistent. | Identical spacing. | `NO_GAP` | No code change. |
| **3. Lunar calendar top card: phase chips** | Key phase buttons are styled with `border` and `background` derived from phase-specific OKLCH colors. | Styled with the exact same OKLCH border/bg variables. | `NO_GAP` | No code change. |
| **3. Lunar calendar top card: strip glyphs** | Displays horizontal scroll of SVG phase glyphs for all days in the month. | Displays horizontal scroll of SVG phase glyphs. | `NO_GAP` | No code change. |
| **3. Lunar calendar top card: percent labels** | Renders illumination percentage under each glyph. | Renders illumination percentage. | `NO_GAP` | No code change. |
| **3. Lunar calendar top card: legend** | Shows legend at the bottom of the card: новолуние, полнолуние, четверть, and "±1 день" (with an Info icon). | Shows legend but is missing the "±1 день" Info icon and text. | `STYLE_GAP` | Add the Lucide `Info` icon and "±1 день" label to the legend list in `lunar-calendar-strip.tsx`. |
| **3. Lunar calendar top card: selected detail** | Expands with `AnimatePresence` and renders a detailed card: 36px phase glyph, phase name/description, sign symbol, name, and element badges. | Shows a simple static `flex-wrap` line of text with a 24px glyph and basic attributes. | `STYLE_GAP` | Re-write the selected detail card in `lunar-calendar-strip.tsx` to match the oracle's layout, SVG size, elements, and `AnimatePresence` animation. |
| **4. Day-mode grid: cell spacing** | Standard 7-column grid layout. | Standard 7-column grid layout. | `NO_GAP` | No code change. |
| **4. Day-mode grid: selected day circle** | Highlights selected day with a solid primary-colored circle. | Highlights selected day with a solid primary-colored circle. | `NO_GAP` | No code change. |
| **4. Day-mode grid: out-of-month opacity** | Out-of-month cells have opacity 35%. | Out-of-month cells have opacity 35%. | `NO_GAP` | No code change. |
| **4. Day-mode grid: lock icon position** | Locks are positioned absolutely at the top right of the cell (`right-1.5 top-1.5`) with `h-[9px] w-[9px]`. | Locks are positioned identically. | `NO_GAP` | No code change. |
| **4. Day-mode grid: secondary marker** | Renders `MoodIcon` emoji: supportive (⭐), even (◐), tense (⚠️) inside a circular background badge. | Renders Lucide SVG icons (Flame, Sparkles, Minus) under day numbers. | `STYLE_GAP` | Modify `MoodIcon` to render the emoji-based circular badge matching the oracle. Remove Lucide icons. |
| **5. Moon-mode grid: phase glyph shape** | Renders 18px SVG phase glyphs for all days in the month (using `PhaseGlyph`). | Renders 18px SVG phase glyphs (using `PhaseGlyph`). | `NO_GAP` | No code change (verified that test requires SVG). |
| **5. Moon-mode grid: lunar day number** | Renders the lunar day number below the phase glyph. | Renders the lunar day number below the phase glyph. | `NO_GAP` | No code change. |
| **5. Moon-mode grid: selected ring** | Shows selected cell with `bg-primary/10` and `ring-2 ring-primary` (high contrast). | Shows selected cell with `bg-primary/10` and `ring-2 ring-primary/50` (lower contrast). | `STYLE_GAP` | Adjust selected ring in moon-mode to `ring-primary` instead of `ring-primary/50`. |
| **5. Moon-mode grid: current-day orange marker** | Does not render an orange dot for today. Today has `ring-1 ring-border`. Void of Course (VoC) has a `bg-amber-500` dot at `-right-0.5 -top-0.5`. | Renders a `bg-amber-500` dot for today at `-right-0.5 -top-0.5` and a `bg-amber-500` dot for VoC at `right-1 top-1`. | `STYLE_GAP` | Remove the `isToday` orange dot from moon-mode. Place the `voidOfCourse` orange dot at `-right-0.5 -top-0.5`. |
| **5. Moon-mode grid: out-of-month opacity** | Out-of-month cells have `opacity-30` applied to the entire cell button (dimming the SVG phase glyph). | Out-of-month cells only get text color opacity, leaving the SVG phase glyph fully opaque. | `STYLE_GAP` | Apply `opacity-30` to the entire cell button when `!day.isCurrentMonth`. |
| **6. Bottom selected-day summary: height/typo** | Fixed-height container with serif title and status/lunar metadata. | Matching container layout. | `NO_GAP` | No code change. |
| **6. Bottom selected-day summary: CTA position** | Button is positioned at the right side of the summary. | Button is positioned at the right side of the summary. | `NO_GAP` | No code change. |
| **6. Bottom selected-day summary: metadata formatting** | Moon mode shows dot separators `·` and a rounded badge for VoC (`bg-amber-500/15` + orange dot + "без курса"). | Moon mode shows plain text values with no separators and a basic "Луна без курса" label. | `STYLE_GAP` | Reformat moon summary metadata to include `·` dot separators and the styled `без курса` badge. |
| **7. Bottom nav overlap & viewport fit** | summary container remains fully visible above the bottom navigation bar. | Summary container remains fully visible above the bottom navigation bar. | `NO_GAP` | No code change. |
