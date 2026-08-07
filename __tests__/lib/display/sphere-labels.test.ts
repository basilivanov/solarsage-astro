// ############################################################################
// AI_HEADER: MODULE_TESTS_LIB_DISPLAY_SPHERE_LABELS
// ROLE: Unit tests for the sphere key display mapping helper.
// ############################################################################

import { describe, it, expect } from "vitest";
import {
  getSphereLabel,
  getPlanetLabel,
  PRODUCT_SPHERE_META,
  CANONICAL_PRODUCT_ORDER,
} from "../../../lib/display/sphere-labels";

describe("getSphereLabel", () => {
  it("maps canonical product keys to human-readable Russian labels", () => {
    expect(getSphereLabel("work")).toBe("Работа");
    expect(getSphereLabel("finance")).toBe("Финансы");
    expect(getSphereLabel("home_family")).toBe("Дом и семья");
    expect(getSphereLabel("friends_goals")).toBe("Друзья и планы");
  });

  it("does not display raw technical keys to the user", () => {
    const label = getSphereLabel("unknown_technical_key");
    expect(label).not.toContain("unknown_technical_key");
    expect(label).not.toContain("_");
  });

  it("does not reintroduce removed product keys", () => {
    expect(getSphereLabel("decisions")).toBe("Другая сфера");
    expect(getSphereLabel("shopping")).toBe("Другая сфера");
  });

  it("formats unknown keys as safe generic Russian text", () => {
    const label = getSphereLabel("some_unknown_key");
    expect(label).toBe("Другая сфера");
    expect(label).not.toContain("_");
  });

  it("handles empty key with fallback", () => {
    expect(getSphereLabel("")).toBe("Сфера");
  });

  it("handles whitespace-only key with fallback", () => {
    expect(getSphereLabel("  ")).toBe("Сфера");
  });

  it("keeps exactly twelve canonical product buckets with metadata", () => {
    const canonicalKeys = new Set(CANONICAL_PRODUCT_ORDER.map(c => c.key));
    expect(CANONICAL_PRODUCT_ORDER).toHaveLength(12);
    expect(canonicalKeys.size).toBe(12);
    expect(canonicalKeys.has("decisions" as never)).toBe(false);
    expect(canonicalKeys.has("shopping" as never)).toBe(false);

    for (const productKey of canonicalKeys) {
      const meta = PRODUCT_SPHERE_META[productKey];
      expect(meta).toBeDefined();
      expect(meta.label).toBeDefined();
      expect(meta.icon).toBeDefined();
    }
  });
});

describe("getPlanetLabel", () => {
  it("returns RU labels for known planets and falls back to the raw name", () => {
    expect(getPlanetLabel("Sun")).toBe("Солнце");
    expect(getPlanetLabel("Moon")).toBe("Луна");
    expect(getPlanetLabel("Pluto")).toBe("Плутон");
    expect(getPlanetLabel("Chiron")).toBe("Chiron");
  });
});
