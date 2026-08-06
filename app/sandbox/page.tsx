// ############################################################################
// AI_HEADER: MODULE_SANDBOX_INDEX — lists available prototype screens and fixtures.
// ROLE: Entry point of the dev-only sandbox; links every registered preview.
// ############################################################################

// START_MODULE_CONTRACT: M-SANDBOX-INDEX
// purpose: Render the sandbox directory of screens and fixture states for quick visual review.
// owns:
//   - app/sandbox/page.tsx
// inputs: fixture files on disk (read-only directory listing).
// outputs: link list to /sandbox/<screen>?fixture=<name>.
// dependencies: node fs, sandbox registry.
// side_effects: none.
// emitted_logs: none.
// invariants: only fixtures present on disk are listed.
// failure_policy: missing fixture directory renders an empty list.
// END_MODULE_CONTRACT: M-SANDBOX-INDEX

// START_MODULE_MAP: M-SANDBOX-INDEX
// public_entrypoints:
//   - SandboxIndexPage
// semantic_blocks:
//   - DIRECTORY: fixture listing and links.
// owned_tests:
//   - none (dev tooling)
// END_MODULE_MAP: M-SANDBOX-INDEX

import { readdirSync } from "node:fs";
import path from "node:path";

const FIXTURE_DIR = path.join(process.cwd(), "__tests__", "fixtures", "today_convergence_v2");

// START_BLOCK: DIRECTORY
export default function SandboxIndexPage() {
  let fixtures: string[] = [];
  try {
    fixtures = readdirSync(FIXTURE_DIR)
      .filter((name) => name.endsWith(".json"))
      .map((name) => name.replace(/\.json$/, ""))
      .sort();
  } catch {
    fixtures = [];
  }

  return (
    <main className="mx-auto w-full max-w-2xl px-5 py-8 font-sans">
      <h1 className="font-serif text-[24px] leading-[30px]">Sandbox</h1>
      <p className="mt-2 text-[13px] leading-5 text-muted-foreground">
        Прототипы рендерятся настоящими компонентами на локальных фикстурах. Dev-only.
      </p>
      <h2 className="mt-6 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
        Экран дня (today)
      </h2>
      <ul className="mt-2 space-y-1">
        {fixtures.map((name) => (
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
// END_BLOCK: DIRECTORY
