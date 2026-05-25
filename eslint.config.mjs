// ESLint flat config — GRACE W-2.0 frontend enforcement (variant C, lint half).
// The whitelist of enforced paths mirrors grace/frontend.paths so that ESLint
// and the bash marker gate police the same surface area.

import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import grace from "./eslint-rules/grace-plugin.mjs";

// Mirror of grace/frontend.paths. Kept in sync manually; check-markers.sh and
// check-negative.sh both read the .paths file at runtime, this config does not
// require dynamic loading because flat-config files are evaluated once.
const ENFORCED_GLOBS = [
  "app/(grace)/**/*.{ts,tsx}",
  "components/grace/**/*.{ts,tsx}",
  "lib/grace/**/*.ts",
  "lib/api/**/*.ts",
  "packages/contracts/index.ts",
];

export default [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "apps/api/**",
      "packages/contracts/_generated.ts",
      "packages/contracts/openapi.json",
      "user_read_only_context/**",
      "grace/**",
      "scripts/**",
      "eslint-rules/**",
      // Legacy frontend snapshot. Lives outside the GRACE perimeter and outside
      // the Next.js app/ tree. Kept in-tree so packets W-2.1..W-2.8 can pull
      // files into app/(grace)/** with markers without juggling two zips.
      "legacy/**",
    ],
  },
  js.configs.recommended,
  {
    files: ENFORCED_GLOBS,
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: { grace },
    rules: {
      "grace/contracts-only-import": "error",
      "grace/no-redeclare-contract-types": "error",
      "no-unused-vars": "off",
      "no-undef": "off",
    },
  },
];
