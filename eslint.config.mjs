// ESLint flat config — GRACE W-2.0 frontend enforcement (variant C, lint half).
// The whitelist of enforced paths mirrors grace/frontend.paths so that ESLint
// and the bash marker gate police the same surface area.

import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import grace from "./eslint-rules/grace-plugin.mjs";
import reactHooks from "eslint-plugin-react-hooks";

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

// Browser/DOM/React globals used across the codebase.
// TypeScript's lib: ["dom"] provides these at compile time; ESLint's
// no-undef needs explicit globals to avoid false positives.
const BROWSER_GLOBALS = {
  // DOM / browser APIs
  window: "readonly",
  document: "readonly",
  fetch: "readonly",
  console: "readonly",
  setTimeout: "readonly",
  clearTimeout: "readonly",
  setInterval: "readonly",
  clearInterval: "readonly",
  requestAnimationFrame: "readonly",
  cancelAnimationFrame: "readonly",
  localStorage: "readonly",
  sessionStorage: "readonly",
  crypto: "readonly",
  URLSearchParams: "readonly",
  TextEncoder: "readonly",
  self: "readonly",
  confirm: "readonly",
  global: "readonly",
  process: "readonly",
  // React namespace (available via automatic JSX runtime + @types/react)
  React: "readonly",
  // DOM TypeScript interfaces (provided by lib: ["dom"])
  Element: "readonly",
  HTMLElement: "readonly",
  HTMLDivElement: "readonly",
  HTMLButtonElement: "readonly",
  HTMLInputElement: "readonly",
  HTMLTextAreaElement: "readonly",
  HTMLAnchorElement: "readonly",
  // DOM event types (provided by lib: ["dom"])
  KeyboardEvent: "readonly",
  MouseEvent: "readonly",
  PointerEvent: "readonly",
};

export default [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "apps/api/**",
      "apps/solarsage/**",
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
  // Browser/DOM globals for all files
  { languageOptions: { globals: BROWSER_GLOBALS } },
  js.configs.recommended,
  // Allow _-prefixed unused vars/args (TypeScript convention).
  // ENFORCED_GLOBS block below sets no-unused-vars: "off" to let GRACE
  // contracts-only-import do the policing instead.
  {
    rules: {
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    },
  },
  // React Hooks rules — apply to ALL tsx files (catches Rules of Hooks violations early)
  {
    files: ["**/*.tsx", "**/*.jsx"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
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
    plugins: { grace, "react-hooks": reactHooks },
    rules: {
      "grace/contracts-only-import": "error",
      "grace/no-redeclare-contract-types": "error",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "no-unused-vars": "off",
      "no-undef": "off",
    },
  },
];
