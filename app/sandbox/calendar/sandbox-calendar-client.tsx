// ############################################################################
// AI_HEADER: MODULE_SANDBOX_CALENDAR_CLIENT — client frame for the Calendar prototype.
// ROLE: Renders the real CalendarScreen with a fixture payload inside the app shell frame.
// ############################################################################

// START_MODULE_CONTRACT: M-SANDBOX-CALENDAR-CLIENT
// purpose: Compose the real CalendarScreen and TabBar around a fixture payload for visual iteration.
// owns:
//   - app/sandbox/calendar/sandbox-calendar-client.tsx
// inputs: validated calendar/v2 payload and its fixture name.
// outputs: app-framed interactive preview; fixture badge.
// dependencies: CalendarScreen; TabBar.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - no auth, no API calls from the frame itself; the screen never fetches (initialPayload seam).
//   - the frame keeps the production /calendar canvas (phone-width column, no wide lg layout).
// failure_policy: fixture shape errors surface as the screen's own error states.
// END_MODULE_CONTRACT: M-SANDBOX-CALENDAR-CLIENT

// START_MODULE_MAP: M-SANDBOX-CALENDAR-CLIENT
// public_entrypoints:
//   - SandboxCalendarClient
// semantic_blocks:
//   - FRAME: app-shell-like container, phone-width like the /calendar route.
//   - THEME: ?theme= override / prefers-color-scheme dark toggle for the preview.
// owned_tests:
//   - none (dev tooling)
// END_MODULE_MAP: M-SANDBOX-CALENDAR-CLIENT

"use client";

import { useEffect } from "react";
import type { CalendarPayload } from "@/packages/contracts";
import { CalendarScreen } from "@/components/calendar/calendar-screen";
import { TabBar } from "@/components/today/tab-bar";

type Props = {
  payload: CalendarPayload;
  fixtureName: string;
};

// START_BLOCK: THEME
// ?theme=dark|light forces the html.dark class (as telegram-init does in production);
// without the param the preview follows prefers-color-scheme.
function useSandboxTheme() {
  useEffect(() => {
    const root = document.documentElement;
    const param = new URLSearchParams(window.location.search).get("theme");
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = param ? param === "dark" : media.matches;
      root.classList.toggle("dark", dark);
    };
    apply();
    media.addEventListener("change", apply);
    return () => {
      media.removeEventListener("change", apply);
      root.classList.remove("dark");
    };
  }, []);
}
// END_BLOCK: THEME

// START_BLOCK: FRAME
export function SandboxCalendarClient({ payload, fixtureName }: Props) {
  useSandboxTheme();
  return (
    <main className="h-[var(--app-height)] overflow-hidden bg-background">
      <div className="mx-auto flex h-full max-w-md flex-col border-x border-border/50 bg-background">
        <div className="flex-none border-b border-border/40 bg-secondary/40 px-4 py-1.5 text-center text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
          sandbox · {fixtureName}
        </div>
        <div className="flex-1 overflow-y-auto overscroll-contain">
          <CalendarScreen initialPayload={payload} onOpenDay={() => {}} />
        </div>
        <TabBar />
      </div>
    </main>
  );
}
// END_BLOCK: FRAME
