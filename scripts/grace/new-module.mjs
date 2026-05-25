#!/usr/bin/env node
// GRACE W-2.0 module template generator.
// Usage:
//   node scripts/grace/new-module.mjs <kind> <module-id> <out-path>
//   kind = page | component | lib
// Example:
//   node scripts/grace/new-module.mjs page M-WEB-NATAL.page "app/(grace)/natal/page.tsx"
//
// Emits a file that already passes scripts/grace/check-markers.sh. The author
// then fills in invariants, owned_tests, and the body. The template is
// deliberately minimal: GRACE markers + one BODY block as a placeholder.

import { writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const [, , kind, moduleId, outPath] = process.argv;
if (!kind || !moduleId || !outPath) {
  console.error("usage: new-module.mjs <page|component|lib> <module-id> <out-path>");
  process.exit(2);
}
if (!["page", "component", "lib"].includes(kind)) {
  console.error(`unknown kind: ${kind}`);
  process.exit(2);
}
if (existsSync(outPath)) {
  console.error(`refusing to overwrite ${outPath}`);
  process.exit(2);
}

const isLib = kind === "lib";
const ext = isLib ? "ts" : "tsx";

const tpl = `// ############################################################################
// AI_HEADER: ${moduleId.replace(/[^A-Z0-9_]/gi, "_").toUpperCase()}
// ROLE: <one-line role>
// DEPENDENCIES: <comma-separated list>
// GRACE_ANCHORS: [BODY]
// ############################################################################

// START_MODULE_CONTRACT: ${moduleId}
// purpose: <why this module exists>
// owns:
//   - ${outPath}
// inputs:
//   - <inputs>
// outputs:
//   - <outputs>
// dependencies:
//   - <upstream modules / contracts>
// side_effects:
//   - <none | http | stdout | ...>
// invariants:
//   - <invariant 1>
// failure_policy:
//   - <how this module reacts to upstream failure>
// non_goals:
//   - <explicit non-goals>
// END_MODULE_CONTRACT: ${moduleId}

// START_MODULE_MAP: ${moduleId}
// public_entrypoints:
//   - <entry 1>
// semantic_blocks:
//   - BODY
// owned_tests:
//   - <path to test>
// END_MODULE_MAP: ${moduleId}

${kind === "page"
  ? `export default function Page() {
  // START_BLOCK: BODY
  return null;
  // END_BLOCK: BODY
}
`
  : kind === "component"
  ? `export function Component() {
  // START_BLOCK: BODY
  return null;
  // END_BLOCK: BODY
}
`
  : `// START_BLOCK: BODY
export {};
// END_BLOCK: BODY
`}`;

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, tpl);
console.log(`[grace-new-module] wrote ${outPath} (${ext}, ${kind})`);
