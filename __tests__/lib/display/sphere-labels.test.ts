// ############################################################################
// AI_HEADER: MODULE_TESTS_LIB_DISPLAY_SPHERE_LABELS
// ROLE: Unit tests for the sphere key display mapping helper.
// ############################################################################

import { describe, it, expect } from "vitest";
import { getSphereLabel } from "../../../lib/display/sphere-labels";

describe("getSphereLabel", () => {
  it("maps known technical keys to human-readable Russian labels", () => {
    expect(getSphereLabel("work_status_achievement")).toBe("Карьера и достижения");
    expect(getSphereLabel("relationships_partnership")).toBe("Отношения и партнёрство");
    expect(getSphereLabel("body_energy_health")).toBe("Энергия и здоровье");
    expect(getSphereLabel("home_family")).toBe("Дом и семья");
  });

  it("maps creativity_self_expression correctly", () => {
    expect(getSphereLabel("creativity_self_expression")).toBe("Творчество и самовыражение");
  });

  it("does not display raw technical keys to the user", () => {
    // The raw key "work_status_achievement" must NOT appear in the label
    const label = getSphereLabel("work_status_achievement");
    expect(label).not.toContain("work_status_achievement");
    expect(label).not.toContain("_");
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
