// ############################################################################
// AI_HEADER: MODULE_TESTS_LIB_DISPLAY_SPHERE_LABELS
// ROLE: Unit tests for the sphere key display mapping helper.
// ############################################################################

import { describe, it, expect } from "vitest";
import { getSphereLabel } from "../../../lib/display/sphere-labels";

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

  it("formats unknown keys as readable text", () => {
    const label = getSphereLabel("some_unknown_key");
    expect(label).toBe("Some Unknown Key");
    expect(label).not.toContain("_");
  });

  it("handles empty key with fallback", () => {
    expect(getSphereLabel("")).toBe("Сфера");
  });

  it("handles whitespace-only key with fallback", () => {
    expect(getSphereLabel("  ")).toBe("Сфера");
  });
});
