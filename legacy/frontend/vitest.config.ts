import { defineConfig } from "vitest/config"
import path from "path"

export default defineConfig({
  test: {
    globals: true,
    environment: "node", // Не jsdom — тестируем чистую логику
    include: ["**/*.test.ts"],
    exclude: ["node_modules", "e2e"],
    coverage: {
      provider: "v8",
      include: ["lib/contracts/**", "lib/reducers/**"],
      reporter: ["text", "json", "html"],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
})
