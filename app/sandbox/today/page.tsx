// ############################################################################
// AI_HEADER: MODULE_SANDBOX_TODAY — fixture-driven live prototype of the Today screen.
// ROLE: Loads one committed Today fixture and renders the real TodayScreen in an app frame.
// ############################################################################

// START_MODULE_CONTRACT: M-SANDBOX-TODAY
// purpose: Preview the real Today screen against a local JSON fixture without auth or API.
// owns:
//   - app/sandbox/today/page.tsx
// inputs: ?fixture=<name> query matching __tests__/fixtures/today_convergence_v2/<name>.json.
// outputs: rendered TodayScreen inside a phone/desktop frame with TabBar.
// dependencies: node fs; TodayScreen; TabBar.
// side_effects: reads fixture files from disk at request time.
// emitted_logs: none.
// invariants: unknown or malformed fixture names render a picker, never throw to the user.
// failure_policy: invalid fixture renders a plain picker page listing valid names.
// END_MODULE_CONTRACT: M-SANDBOX-TODAY

// START_MODULE_MAP: M-SANDBOX-TODAY
// public_entrypoints:
//   - SandboxTodayPage
// semantic_blocks:
//   - FIXTURE_LOAD: safe on-disk fixture resolution.
//   - FRAME: app-like shell around the real screen.
// owned_tests:
//   - none (dev tooling)
// END_MODULE_MAP: M-SANDBOX-TODAY

import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";

import { SandboxTodayClient } from "./sandbox-today-client";

const FIXTURE_DIR = path.join(process.cwd(), "__tests__", "fixtures", "today_convergence_v2");
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

function loadFixture(name: string): unknown | null {
  if (!FIXTURE_NAME_RE.test(name)) return null;
  try {
    return JSON.parse(readFileSync(path.join(FIXTURE_DIR, `${name}.json`), "utf-8"));
  } catch {
    return null;
  }
}
// END_BLOCK: FIXTURE_LOAD

export default async function SandboxTodayPage({
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
        <h1 className="font-serif text-[22px] leading-[28px]">Sandbox · today</h1>
        <p className="mt-2 text-[13px] text-muted-foreground">
          {fixture ? `Фикстура «${fixture}» не найдена.` : "Выбери фикстуру:"}
        </p>
        <ul className="mt-4 space-y-1">
          {names.map((name) => (
            <li key={name}>
              <a
                className="text-[14px] leading-6 text-primary underline-offset-4 hover:underline"
                href={`/sandbox/today?fixture=${encodeURIComponent(name)}`}
              >
                {name}
              </a>
            </li>
          ))}
        </ul>
      </main>
    );
  }

  return <SandboxTodayClient payload={payload} fixtureName={fixture ?? "unknown"} />;
}
