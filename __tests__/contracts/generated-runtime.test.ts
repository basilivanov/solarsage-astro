// ############################################################################
// AI_HEADER: TEST_CONTRACTS_GENERATED_RUNTIME — integration test for generated zod schemas
// ROLE: Proves that generated runtime zod schemas correctly parse valid API payloads.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CONTRACTS-GENERATED-RUNTIME
// purpose: Validate generated zod schema behaviors on canonical fixtures.
// owns:
//   - __tests__/contracts/generated-runtime.test.ts
// inputs: mock payloads, e2e fixture
// outputs: vitest assertions
// dependencies: packages/contracts/runtime.ts, e2e fixture
// side_effects: none
// emitted_logs: none
// invariants:
//   - generated schemas must accept unknown fields
//   - missing required fields must be rejected
// failure_policy: fail test
// END_MODULE_CONTRACT: M-TEST-CONTRACTS-GENERATED-RUNTIME

// START_MODULE_MAP: M-TEST-CONTRACTS-GENERATED-RUNTIME
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - SCHEMA_TESTS: validates generated zod schema parsing and constraints
// owned_tests:
//   - __tests__/contracts/generated-runtime.test.ts
// END_MODULE_MAP: M-TEST-CONTRACTS-GENERATED-RUNTIME

// START_BLOCK: SCHEMA_TESTS
import { describe, expect, it } from "vitest"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"
import {
  TodayPayloadWireSchema,
  TodayV2BlockWireSchema,
  TodayV2HorizonsBlockWireSchema,
  ActivationEvidenceWireSchema,
} from "@/packages/contracts/runtime"
import {
  HoraryAnswerRead,
  NatalSection,
} from "@/packages/contracts/_generated.zod"

describe("generated runtime zod schemas", () => {
  it("parses a canonical valid API payload", () => {
    const parsed = TodayPayloadWireSchema.safeParse(dayPayloadV2)
    expect(parsed.success).toBe(true)
    expect(TodayV2HorizonsBlockWireSchema.safeParse(dayPayloadV2.v2?.horizons).success).toBe(true)
  })

  it("accepts previous v2 identity and current fixture carries pipeline audit", () => {
    const previous: Record<string, unknown> = structuredClone(dayPayloadV2)
    const previousMeta = previous.meta as Record<string, unknown>
    const previousV2 = previous.v2 as Record<string, unknown>
    const previousAudit = previousV2.audit as Record<string, unknown>
    previousMeta.payloadVersion = "today.v2"
    previousMeta.frontendPayloadVersion = 2
    previousAudit.payloadVersion = "today.v2"
    delete previousAudit.horizonPipeline
    expect(TodayPayloadWireSchema.safeParse(previous).success).toBe(true)

    expect(dayPayloadV2.meta.payloadVersion).toBe("today.v2.1")
    expect(dayPayloadV2.meta.frontendPayloadVersion).toBe(3)
    expect(dayPayloadV2.v2!.audit.horizonPipeline).toEqual({
      schemaVersion: "today-horizon-pipeline-audit.v1",
      status: "built",
      reason: "selected",
      selectedCount: 3,
    })
  })

  it("rejects structurally invalid horizon audit union values", () => {
    const invalidAudit: Record<string, unknown> = structuredClone(dayPayloadV2)
    const invalidV2 = invalidAudit.v2 as Record<string, unknown>
    const invalidAuditBlock = invalidV2.audit as Record<string, unknown>
    invalidAuditBlock.horizonPipeline = {
      schemaVersion: "today-horizon-pipeline-audit.v1",
      status: "built",
      reason: "missing_fast",
      selectedCount: 0,
    }
    expect(TodayPayloadWireSchema.safeParse(invalidAudit).success).toBe(false)
  })

  it("rejects missing required root field", () => {
    const malformed: Record<string, unknown> = { ...dayPayloadV2 }
    delete malformed.date
    const parsed = TodayPayloadWireSchema.safeParse(malformed)
    expect(parsed.success).toBe(false)
  })

  it("validates V2 nested activation fields", () => {
    const evidence = dayPayloadV2.v2!.activationEvidence[0]
    expect(ActivationEvidenceWireSchema.safeParse(evidence).success).toBe(true)

    const malformedEvidence: Record<string, unknown> = { ...evidence }
    delete malformedEvidence.id
    expect(ActivationEvidenceWireSchema.safeParse(malformedEvidence).success).toBe(false)
  })

  it("does not reject unknown additive fields (forward compatibility)", () => {
    const additivePayload = {
      ...dayPayloadV2,
      extraNewFieldFromFutureBackend: "yes",
      v2: {
        ...dayPayloadV2.v2,
        horizons: {
          ...dayPayloadV2.v2!.horizons,
          futureBackendField: "allowed-and-stripped",
        },
      },
    }
    const parsed = TodayPayloadWireSchema.safeParse(additivePayload)
    expect(parsed.success).toBe(true)
    expect(parsed.success && Reflect.has(parsed.data.v2!.horizons as object, "futureBackendField")).toBe(false)
  })

  it("rejects invalid horizon tone and timing scalar", () => {
    const malformedTone = structuredClone(dayPayloadV2)
    malformedTone.v2!.horizons!.items[0].tone = "bad-tone" as never
    expect(TodayPayloadWireSchema.safeParse(malformedTone).success).toBe(false)

    const malformedTiming = structuredClone(dayPayloadV2)
    malformedTiming.v2!.horizons!.items[1].timing.precision = "bad-precision" as never
    expect(TodayPayloadWireSchema.safeParse(malformedTiming).success).toBe(false)
  })

  it("accepts null or absent horizons for rolling fallback", () => {
    const nullHorizons = {
      ...dayPayloadV2,
      v2: {
        ...dayPayloadV2.v2!,
        audit: {
          ...dayPayloadV2.v2!.audit,
          horizonPipeline: {
            schemaVersion: "today-horizon-pipeline-audit.v1",
            status: "unavailable",
            reason: "missing_fast",
            selectedCount: 0,
          },
        },
        horizons: null,
      },
    }
    expect(TodayPayloadWireSchema.safeParse(nullHorizons).success).toBe(true)

    const absentHorizons = structuredClone(dayPayloadV2)
    absentHorizons.v2!.audit.horizonPipeline = {
      schemaVersion: "today-horizon-pipeline-audit.v1",
      status: "unavailable",
      reason: "missing_fast",
      selectedCount: 0,
    }
    delete (absentHorizons.v2 as Record<string, unknown>).horizons
    expect(TodayPayloadWireSchema.safeParse(absentHorizons).success).toBe(true)
  })

  it("proves that generated zod validator rejects wrong known timing type", () => {
    const evidence = dayPayloadV2.v2!.activationEvidence[0]
    const malformedEvidence = {
      ...evidence,
      activeFrom: 123, // should be string or null
    }
    expect(ActivationEvidenceWireSchema.safeParse(malformedEvidence).success).toBe(false)
  })

  it("proves that importing _generated.zod.ts no longer throws and discriminated union is functional", () => {
    // TodayV2BlockWireSchema parses dayPayloadV2.v2
    expect(TodayV2BlockWireSchema.safeParse(dayPayloadV2.v2).success).toBe(true)

    // 2. generated horary paragraph branch contains literal discriminator
    // 3. valid HoraryAnswerRead sample с type: "paragraph" parses
    const validHoraryAnswer = {
      verdict: "yes",
      confidence: 0.8,
      generatedAt: "2026-07-11T12:00:00Z",
      planets: ["Moon"],
      blocks: [
        {
          type: "paragraph",
          text: "Test paragraph",
        },
      ],
    }
    expect(HoraryAnswerRead.safeParse(validHoraryAnswer).success).toBe(true)

    // 4. unknown horary type rejects
    const invalidHoraryAnswer = {
      ...validHoraryAnswer,
      blocks: [
        {
          type: "unknown_future_type",
          text: "Test",
        },
      ],
    }
    expect(HoraryAnswerRead.safeParse(invalidHoraryAnswer).success).toBe(false)

    // 5. missing discriminator in a discriminated parent rejects
    const missingDiscrimHoraryAnswer = {
      ...validHoraryAnswer,
      blocks: [
        {
          text: "Test",
        },
      ],
    }
    expect(HoraryAnswerRead.safeParse(missingDiscrimHoraryAnswer).success).toBe(false)

    // 6. valid NatalSection sample parses
    const validNatalSection = {
      id: "sec-1",
      title: "Test Natal",
      blocks: [
        {
          type: "paragraph",
          text: "Natal paragraph",
        },
      ],
    }
    expect(NatalSection.safeParse(validNatalSection).success).toBe(true)
  })

  it("verifies generated zod file imports only from zod and has no @zodios/core", () => {
    // 9. generated file imports runtime only from "zod"
    // 10. generated file does not contain "@zodios/core" or HTTP client
    const fs = require("fs")
    const path = require("path")
    const content: string = fs.readFileSync(path.resolve(__dirname, "../../packages/contracts/_generated.zod.ts"), "utf8")

    // 1. Собрать все top-level import lines generated file.
    // 2. Доказать, что их ровно одна и это import from zod.
    const importLines = content.split("\n").filter(line => line.trim().startsWith("import "))
    expect(importLines).toHaveLength(1)
    expect(importLines[0]).toMatch(/^import\s+\{\s*z\s*\}\s+from\s+["']zod["'];?$/)

    // 3. Доказать отсутствие:
    expect(content).not.toContain("@zodios/core")
    expect(content).not.toContain("Zodios")
    expect(content).not.toContain("zodios")
    expect(content).not.toContain("axios")
    expect(content).not.toContain("createApiClient")
    expect(content).not.toContain("fetch(")

    // Проверка endpoints должна быть word-aware
    const wordEndpointsRegex = /\bendpoints\b/
    expect(wordEndpointsRegex.test(content)).toBe(false)
  })

  it("proves that normalizer throws on invalid, contradictory or unsupported schemas", () => {
    const { normalizeOpenAPIDocument } = require("../../scripts/contracts/generate-zod.cjs");

    // const becomes singleton enum
    const doc1 = {
      components: {
        schemas: {
          Test: {
            properties: {
              type: {
                const: "paragraph",
              },
            },
          },
        },
      },
    };
    normalizeOpenAPIDocument(doc1);
    const typeObject = Reflect.get(doc1.components.schemas.Test.properties, "type");
    expect(Reflect.get(typeObject, "enum")).toEqual(["paragraph"]);

    // const=a + enum=[a,b]: normalizer narrows to [a]
    const docNarrow = {
      components: {
        schemas: {
          Test: {
            properties: {
              type: {
                const: "a",
                enum: ["a", "b"],
              },
            },
          },
        },
      },
    };
    normalizeOpenAPIDocument(docNarrow);
    const narrowObject = Reflect.get(docNarrow.components.schemas.Test.properties, "type");
    expect(Reflect.get(narrowObject, "enum")).toEqual(["a"]);

    // contradictory const/enum throws
    const doc2 = {
      components: {
        schemas: {
          Test: {
            properties: {
              type: {
                const: "paragraph",
                enum: ["lead"],
              },
            },
          },
        },
      },
    };
    expect(() => normalizeOpenAPIDocument(doc2)).toThrow();

    // inline oneOf branch throws
    const doc3 = {
      components: {
        schemas: {
          Parent: {
            discriminator: {
              propertyName: "type",
            },
            oneOf: [
              {
                type: "object",
                properties: {
                  type: { const: "a" },
                },
              },
            ],
          },
        },
      },
    };
    expect(() => normalizeOpenAPIDocument(doc3)).toThrow("inline oneOf branch is forbidden");

    // external ref throws
    const doc4 = {
      components: {
        schemas: {
          Parent: {
            discriminator: {
              propertyName: "type",
            },
            oneOf: [
              {
                $ref: "https://example.com/schemas/child.json",
              },
            ],
          },
        },
      },
    };
    expect(() => normalizeOpenAPIDocument(doc4)).toThrow("external ref");

    // missing discriminator property throws
    const doc5 = {
      components: {
        schemas: {
          Parent: {
            discriminator: {
              propertyName: "type",
            },
            oneOf: [
              {
                $ref: "#/components/schemas/Child",
              },
            ],
          },
          Child: {
            properties: {
              text: { type: "string" },
            },
          },
        },
      },
    };
    expect(() => normalizeOpenAPIDocument(doc5)).toThrow("missing discriminator property");

    // discriminator present + oneOf missing -> throws
    const doc6 = {
      components: {
        schemas: {
          Parent: {
            discriminator: {
              propertyName: "type",
            },
          },
        },
      },
    };
    expect(() => normalizeOpenAPIDocument(doc6)).toThrow("oneOf is empty or not an array");
  })

  it("proves that discriminator property becomes required in referenced branches and is idempotent", () => {
    const { normalizeOpenAPIDocument } = require("../../scripts/contracts/generate-zod.cjs");
    const doc = {
      components: {
        schemas: {
          Parent: {
            discriminator: {
              propertyName: "type",
            },
            oneOf: [
              {
                $ref: "#/components/schemas/Child",
              },
            ],
          },
          Child: {
            properties: {
              type: {
                const: "child",
              },
              text: { type: "string" },
            },
          },
        },
      },
    };

    normalizeOpenAPIDocument(doc);
    const childObject = doc.components.schemas.Child;
    const required = Reflect.get(childObject, "required");
    const properties = Reflect.get(childObject, "properties");
    const typeProperty = Reflect.get(properties, "type");

    expect(Array.isArray(required)).toBe(true);
    expect(required).toContain("type");
    expect((required as string[]).filter((x: string) => x === "type")).toHaveLength(1);
    expect(Reflect.get(typeProperty, "enum")).toEqual(["child"]);

    // normalizer second pass idempotence
    normalizeOpenAPIDocument(doc);
    const requiredSecond = Reflect.get(childObject, "required");
    expect((requiredSecond as string[]).filter((x: string) => x === "type")).toHaveLength(1);
  })

  it("compares generated schemas map with component schema names in canonical OpenAPI document", () => {
    const fs = require("fs")
    const path = require("path")
    const openapi = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../../packages/contracts/openapi.json"), "utf8"))
    const { schemas } = require("../../packages/contracts/_generated.zod.ts")

    const openapiSchemaNames = Object.keys(openapi.components.schemas).sort()
    const generatedSchemaNames = Object.keys(schemas).sort()

    expect(generatedSchemaNames).toEqual(openapiSchemaNames)
  })
})
// END_BLOCK: SCHEMA_TESTS
