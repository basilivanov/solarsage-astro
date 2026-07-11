// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_GENERATE_ZOD — OpenAPI 3.1 discriminator compatibility normalizer.
// ROLE: Loads openapi.json, applies compatibility normalization, and invokes openapi-zod-client programmatically.
// DEPENDENCIES: openapi-zod-client, fs, path
// ############################################################################

// START_MODULE_CONTRACT: M-CONTRACTS-GENERATE-ZOD
// purpose: Normalize openapi.json in-memory and write compatibility-compliant _generated.zod.ts.
// owns:
//   - scripts/contracts/generate-zod.cjs
// inputs:
//   - packages/contracts/openapi.json
//   - scripts/contracts/templates/zod-schemas.hbs
// outputs:
//   - packages/contracts/_generated.zod.ts
// dependencies:
//   - openapi-zod-client
// side_effects:
//   - Reads openapi.json and templates/zod-schemas.hbs
//   - Writes _generated.zod.ts (uses atomic temp file write-and-rename pattern)
// emitted_logs: none
// invariants:
//   - openapi.json is never mutated on disk.
//   - compatibility fixes (const-to-enum, discriminator-required) are applied.
// failure_policy: exits process with non-zero exit code on failure.
// END_MODULE_CONTRACT: M-CONTRACTS-GENERATE-ZOD

// START_MODULE_MAP: M-CONTRACTS-GENERATE-ZOD
// public_entrypoints:
//   - normalizeOpenAPIDocument
//   - main
// semantic_blocks:
//   - OPENAPI_NORMALIZATION: in-memory recursive normalization.
//   - ZOD_GENERATION: invocation of openapi-zod-client generator.
//   - CLI_FAILURE: failure logging and non-zero exit.
// owned_tests:
//   - __tests__/contracts/generated-runtime.test.ts
// END_MODULE_MAP: M-CONTRACTS-GENERATE-ZOD

const fs = require("fs");
const path = require("path");
const { generateZodClientFromOpenAPI } = require("openapi-zod-client");

// START_BLOCK: OPENAPI_NORMALIZATION
// START_FUNCTION_CONTRACT: F-M-CONTRACTS-GENERATE-ZOD.normalizeOpenAPIDocument
// purpose: Normalize schemas recursively in-memory to add compatibility with openapi-zod-client.
// inputs: doc - the openapi document object.
// returns: void (mutates in-memory document clone).
// side_effects: none.
// emitted_logs: none.
// error_behavior: throws on contradictory schemas, inline oneOf branches, external refs, or missing discriminator properties.
// END_FUNCTION_CONTRACT: F-M-CONTRACTS-GENERATE-ZOD.normalizeOpenAPIDocument
function normalizeOpenAPIDocument(doc) {
  if (!doc || typeof doc !== "object") return;

  // Pass A: const to singleton enum
  function passA(obj) {
    if (!obj || typeof obj !== "object") return;

    if ("const" in obj) {
      const val = obj.const;
      if ("enum" in obj) {
        if (!Array.isArray(obj.enum)) {
          throw new Error("Contradictory schema: enum is not an array");
        }
        if (!obj.enum.includes(val)) {
          throw new Error(`Contradictory schema: const "${val}" is not in enum [${obj.enum.join(", ")}]`);
        }
      }
      obj.enum = [val];
    }

    for (const key of Object.keys(obj)) {
      passA(obj[key]);
    }
  }

  passA(doc);

  // Pass B: discriminator property required in referenced branches
  function passB(obj) {
    if (!obj || typeof obj !== "object") return;

    if (obj.discriminator) {
      const propName = obj.discriminator.propertyName;
      if (typeof propName !== "string" || propName.length === 0) {
        throw new Error("unsupported discriminator schema: propertyName is empty or not a string");
      }
      if (!obj.oneOf || !Array.isArray(obj.oneOf) || obj.oneOf.length === 0) {
        throw new Error("unsupported discriminator schema: oneOf is empty or not an array");
      }

      for (const branch of obj.oneOf) {
        if (!branch || typeof branch !== "object") {
          throw new Error("unsupported discriminator schema: oneOf branch is not a non-null object");
        }
        if (!branch.$ref) {
          throw new Error("unsupported discriminator schema: inline oneOf branch is forbidden");
        }
        const ref = branch.$ref;
        if (typeof ref !== "string") {
          throw new Error("unsupported discriminator schema: $ref is not a string");
        }
        if (!ref.startsWith("#/components/schemas/")) {
          throw new Error(`unsupported discriminator schema: external ref "${ref}" is forbidden`);
        }
        const schemaName = ref.substring("#/components/schemas/".length);
        const component = doc.components && doc.components.schemas && doc.components.schemas[schemaName];
        if (!component) {
          throw new Error(`Missing referenced schema: ${schemaName}`);
        }

        if (!component.properties || !component.properties[propName]) {
          throw new Error(`Referenced schema "${schemaName}" is missing discriminator property "${propName}"`);
        }

        const propSchema = component.properties[propName];
        const isSingletonEnum = Array.isArray(propSchema.enum) && propSchema.enum.length === 1;
        if (!isSingletonEnum) {
          throw new Error(`Referenced schema "${schemaName}" discriminator property "${propName}" must have a singleton enum`);
        }
        if ("const" in propSchema && propSchema.enum[0] !== propSchema.const) {
          throw new Error(`Referenced schema "${schemaName}" discriminator property "${propName}" const value does not match singleton enum`);
        }

        if (!component.required) {
          component.required = [];
        }
        if (!component.required.includes(propName)) {
          component.required.push(propName);
        }
      }
    }

    for (const key of Object.keys(obj)) {
      passB(obj[key]);
    }
  }

  passB(doc);
}
// END_BLOCK: OPENAPI_NORMALIZATION

// START_BLOCK: ZOD_GENERATION
// START_FUNCTION_CONTRACT: F-M-CONTRACTS-GENERATE-ZOD.main
// purpose: Load, normalize, generate, and atomically write the generated zod schemas.
// inputs: none.
// returns: Promise<void>
// side_effects: reads files, writes generated file, exits process on failure.
// emitted_logs: none.
// error_behavior: exits process with status 1 on failure.
// END_FUNCTION_CONTRACT: F-M-CONTRACTS-GENERATE-ZOD.main
async function main() {
  const repoRoot = path.resolve(__dirname, "../..");
  const openapiPath = path.join(repoRoot, "packages/contracts/openapi.json");
  const templatePath = path.join(repoRoot, "scripts/contracts/templates/zod-schemas.hbs");
  const outputPath = path.join(repoRoot, "packages/contracts/_generated.zod.ts");
  const tempOutputPath = path.join(repoRoot, "packages/contracts/_generated.zod.ts.tmp");

  try {
    const rawOpenapi = fs.readFileSync(openapiPath, "utf8");
    const doc = JSON.parse(rawOpenapi);

    // Normalize document in-memory (deep clone to prevent any mutation side effects)
    const clonedDoc = JSON.parse(JSON.stringify(doc));
    normalizeOpenAPIDocument(clonedDoc);

    const generatedCode = await generateZodClientFromOpenAPI({
      openApiDoc: clonedDoc,
      templatePath,
      disableWriteToFile: true,
      options: {
        shouldExportAllSchemas: true,
        strictObjects: false,
      },
    });

    if (typeof generatedCode !== "string" || generatedCode.trim().length === 0) {
      throw new Error("Generated code is empty or not a string");
    }

    fs.writeFileSync(tempOutputPath, generatedCode, "utf8");
    fs.renameSync(tempOutputPath, outputPath);

    console.log("generate-zod.cjs: successfully generated _generated.zod.ts");
  } catch (error) {
    // START_BLOCK: CLI_FAILURE
    console.error("generate-zod.cjs: failed to generate zod schemas:", error);
    if (fs.existsSync(tempOutputPath)) {
      try {
        fs.unlinkSync(tempOutputPath);
      } catch (_) {}
    }
    process.exit(1);
    // END_BLOCK: CLI_FAILURE
  }
}

if (require.main === module) {
  main();
}

module.exports = { normalizeOpenAPIDocument, main };
// END_BLOCK: ZOD_GENERATION
