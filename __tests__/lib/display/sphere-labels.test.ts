// ############################################################################
// AI_HEADER: MODULE_TESTS_LIB_DISPLAY_SPHERE_LABELS
// ROLE: Unit tests for the sphere key display mapping helper.
// ############################################################################

import { describe, it, expect } from "vitest";
import { 
  getSphereLabel, 
  getPlanetLabel,
  BACKEND_TO_PRODUCT_KEY_MAP, 
  PRODUCT_SPHERE_META,
  CANONICAL_PRODUCT_ORDER
} from "../../../lib/display/sphere-labels";

describe("getSphereLabel", () => {
  it("maps canon-shaped technical keys to human-readable Russian labels", () => {
    expect(getSphereLabel("thinking_speech_learning")).toBe("Мышление, речь, обучение");
    expect(getSphereLabel("money_security_resources")).toBe("Деньги, безопасность, ресурсы");
    expect(getSphereLabel("home_family_roots")).toBe("Дом, семья, корни");
    expect(getSphereLabel("work_status_achievement")).toBe("Работа, статус, достижения");
    expect(getSphereLabel("relationships_partnership")).toBe("Отношения и партнёрство");
    expect(getSphereLabel("body_energy_health")).toBe("Энергия и здоровье");
  });

  it("does not display raw technical keys to the user", () => {
    const label = getSphereLabel("work_status_achievement");
    expect(label).not.toContain("work_status_achievement");
    expect(label).not.toContain("_");
  });

  it("maps legacy keys as fallback when canon key is absent", () => {
    expect(getSphereLabel("creativity_self_expression")).toBe("Творчество и самовыражение");
    expect(getSphereLabel("home_family")).toBe("Дом и семья");
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

  it("asserts every backend mapping resolves to one of the 12 canonical product buckets", () => {
    const canonicalKeys = new Set(CANONICAL_PRODUCT_ORDER.map(c => c.key));
    
    Object.keys(BACKEND_TO_PRODUCT_KEY_MAP).forEach(key => {
      const productKey = BACKEND_TO_PRODUCT_KEY_MAP[key];
      expect(canonicalKeys.has(productKey)).toBe(true);
      
      const meta = PRODUCT_SPHERE_META[productKey];
      expect(meta).toBeDefined();
      expect(meta.label).toBeDefined();
      expect(meta.icon).toBeDefined();
    });
  });

  it("asserts key mappings for complex keys resolve into canonical product buckets", () => {
    expect(BACKEND_TO_PRODUCT_KEY_MAP["home_family_roots"]).toBe("relationships");
    expect(BACKEND_TO_PRODUCT_KEY_MAP["home_family"]).toBe("relationships");
    expect(BACKEND_TO_PRODUCT_KEY_MAP["crisis_transformation_control"]).toBe("decisions");
    expect(BACKEND_TO_PRODUCT_KEY_MAP["inner_background_unconscious"]).toBe("health");
    expect(BACKEND_TO_PRODUCT_KEY_MAP["meaning_expansion_vector"]).toBe("travel");
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
