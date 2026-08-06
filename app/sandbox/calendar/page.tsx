// ############################################################################
// AI_HEADER: MODULE_SANDBOX_CALENDAR — fixture-driven live prototype of the Calendar screen.
// ROLE: Loads one committed calendar/v2 fixture and renders the real CalendarScreen in an app frame.
// ############################################################################

// START_MODULE_CONTRACT: M-SANDBOX-CALENDAR
// purpose: Preview the real Calendar screen against a local JSON fixture without auth or API.
// owns:
//   - app/sandbox/calendar/page.tsx
// inputs: ?fixture=<name> query matching __tests__/fixtures/calendar_v1/<name>.json.
// outputs: rendered CalendarScreen inside a phone-width frame with TabBar (same canvas as production /calendar).
// dependencies: node fs; CalendarPayloadWireSchema; SandboxCalendarClient.
// side_effects: reads fixture files from disk at request time.
// emitted_logs: none.
// invariants:
//   - unknown or malformed fixture names render a picker, never throw to the user.
//   - only schema-valid calendar/v2 payloads reach the screen.
// failure_policy: invalid fixture renders a plain picker page listing valid names.
// END_MODULE_CONTRACT: M-SANDBOX-CALENDAR

// START_MODULE_MAP: M-SANDBOX-CALENDAR
// public_entrypoints:
//   - SandboxCalendarPage
// semantic_blocks:
//   - FIXTURE_LOAD: safe on-disk fixture resolution and contract validation.
//   - FRAME: picker or app-like shell around the real screen.
// owned_tests:
//   - none (dev tooling)
// END_MODULE_MAP: M-SANDBOX-CALENDAR

import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";

import type { CalendarPayload } from "@/packages/contracts";
import { CalendarPayloadWireSchema } from "@/packages/contracts/runtime";

import { SandboxCalendarClient } from "./sandbox-calendar-client";

const FIXTURE_DIR = path.join(process.cwd(), "__tests__", "fixtures", "calendar_v1");
const FIXTURE_NAME_RE = /^[a-z0-9_-]+$/;

// START_BLOCK: FIXTURE_LOAD
function listFixtures(): string[] {
  try {
    return readdirSync(FIXTURE_DIR)
      .filter((name) => name.endsWith(".json"))
      .map((name) => name.replace(/\.json$/, ""))
      .sort();
  } catch {
    return [];
  }
}

function loadFixture(name: string): CalendarPayload | null {
  if (!FIXTURE_NAME_RE.test(name)) return null;
  try {
    const raw: unknown = JSON.parse(readFileSync(path.join(FIXTURE_DIR, `${name}.json`), "utf-8"));
    const parsed = CalendarPayloadWireSchema.safeParse(raw);
    return parsed.success ? (parsed.data as CalendarPayload) : null;
  } catch {
    return null;
  }
}
// END_BLOCK: FIXTURE_LOAD

export default async function SandboxCalendarPage({
  searchParams,
}: {
  searchParams: Promise<{ fixture?: string }>;
}) {
  const { fixture } = await searchParams;
  const payload = fixture ? loadFixture(fixture) : null;

  if (!payload) {
    const names = listFixtures();
    return (
      <main className="mx-auto w-full max-w-2xl px-5 py-8 font-sans">
        <h1 className="font-serif text-[22px] leading-[28px]">Sandbox · calendar</h1>
        <p className="mt-2 text-[13px] text-muted-foreground">
          {fixture ? `Фикстура «${fixture}» не найдена или не проходит calendar/v2 контракт.` : "Выбери фикстуру:"}
        </p>
        <ul className="mt-4 space-y-1">
          {names.map((name) => (
            <li key={name}>
              <a
                className="text-[14px] leading-6 text-primary underline-offset-4 hover:underline"
                href={`/sandbox/calendar?fixture=${encodeURIComponent(name)}`}
              >
                {name}
              </a>
            </li>
          ))}
        </ul>
      </main>
    );
  }

  return <SandboxCalendarClient payload={payload} fixtureName={fixture ?? "unknown"} />;
}
