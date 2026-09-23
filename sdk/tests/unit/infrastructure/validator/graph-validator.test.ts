import { describe, expect, it } from "vitest";
import { GraphValidator } from "../../../../src/infrastructure/validator/graph-validator.js";
import { GraphValidationError } from "../../../../src/domain/graph-validation-error.js";
import { GraphDocument } from "../../../../src/domain/contracts.js";

describe("GraphValidator", () => {
  it("rejects entities outside the documentation MVP", () => {
    const validator = new GraphValidator();
    expect(() => validator.validateAndCanonicalize({ schema_version: "1.0",
      entities: [{ key: "service:orders", type: "service" }], relations: [], evidence: [] }))
      .toThrow("invalid entity type");
  });
  const validator = new GraphValidator();

  it("validates and canonicalizes a valid graph document", () => {
    const doc: GraphDocument = {
      schema_version: "1.0",
      entities: [
        { key: "feature:b", type: "feature", name: "B Feature" },
        { key: "feature:a", type: "feature", name: "A Feature" },
      ],
      relations: [
        {
          ref: "rel-2",
          source_entity_key: "feature:b",
          type: "depends_on",
          target_entity_key: "feature:a",
          provenance: "declared",
        },
        {
          ref: "rel-1",
          source_entity_key: "feature:a",
          type: "provides",
          target_entity_key: "feature:b",
          provenance: "declared",
        },
      ],
      evidence: [
        { source: "file-z.ts", relation_ref: "rel-2" },
        { source: "file-a.ts", relation_ref: "rel-1" },
      ],
    };

    const validated = validator.validateAndCanonicalize(doc);

    expect(validated.counts).toEqual({ entities: 2, relations: 2, evidence: 2 });
    expect(validated.document.entities.map((e) => e.key)).toEqual(["feature:a", "feature:b"]);
    expect(validated.document.relations.map((r) => r.ref)).toEqual(["rel-1", "rel-2"]);
    expect(validated.document.evidence.map((ev) => ev.source)).toEqual(["file-a.ts", "file-z.ts"]);
    expect(validated.sha256).toHaveLength(64);
  });

  it("accepts null canonical keys allowed by the publication API", () => {
    const doc = {
      schema_version: "1.0",
      entities: [{ key: "feature:a", type: "feature", canonical_key: null }],
      relations: [],
      evidence: [],
    } as unknown as GraphDocument;

    const validated = validator.validateAndCanonicalize(doc);

    expect(validated.document.entities[0].canonical_key).toBeNull();
  });

  it("rejects canonical keys that are neither strings nor null", () => {
    const doc = {
      schema_version: "1.0",
      entities: [{ key: "feature:a", type: "feature", canonical_key: 42 }],
      relations: [],
      evidence: [],
    };

    expect(() => validator.validateAndCanonicalize(doc)).toThrow(GraphValidationError);
  });

  it("rejects invalid schema version", () => {
    const doc = {
      schema_version: "2.0",
      entities: [],
      relations: [],
      evidence: [],
    };
    expect(() => validator.validateAndCanonicalize(doc)).toThrow(GraphValidationError);
  });

  it("rejects unsupported entity types", () => {
    const doc: any = {
      schema_version: "1.0",
      entities: [{ key: "svc-1", type: "unsupported" }],
      relations: [],
      evidence: [],
    };
    expect(() => validator.validateAndCanonicalize(doc)).toThrow(GraphValidationError);
  });

  it("rejects duplicate relation refs", () => {
    const doc: GraphDocument = {
      schema_version: "1.0",
      entities: [{ key: "feature:a", type: "feature" }],
      relations: [
        {
          ref: "dup-ref",
          source_entity_key: "feature:a",
          type: "depends_on",
          target_entity_key: "feature:a",
          provenance: "declared",
        },
        {
          ref: "dup-ref",
          source_entity_key: "feature:a",
          type: "part_of",
          target_entity_key: "feature:a",
          provenance: "declared",
        },
      ],
      evidence: [],
    };
    expect(() => validator.validateAndCanonicalize(doc)).toThrow(GraphValidationError);
  });

  it("rejects dangling relation endpoints", () => {
    const doc: GraphDocument = {
      schema_version: "1.0",
      entities: [{ key: "feature:a", type: "feature" }],
      relations: [
        {
          ref: "rel-1",
          source_entity_key: "feature:a",
          type: "depends_on",
          target_entity_key: "non-existent",
          provenance: "declared",
        },
      ],
      evidence: [],
    };
    expect(() => validator.validateAndCanonicalize(doc)).toThrow(GraphValidationError);
  });

  it("rejects dangling evidence relation refs", () => {
    const doc: GraphDocument = {
      schema_version: "1.0",
      entities: [],
      relations: [],
      evidence: [{ source: "test.ts", relation_ref: "unknown-rel" }],
    };
    expect(() => validator.validateAndCanonicalize(doc)).toThrow(GraphValidationError);
  });

  it("rejects oversized metadata (>64 KiB)", () => {
    const hugeMeta: Record<string, string> = { data: "x".repeat(65536 + 10) };
    const doc: GraphDocument = {
      schema_version: "1.0",
      entities: [{ key: "feature:a", type: "feature", metadata: hugeMeta }],
      relations: [],
      evidence: [],
    };
    expect(() => validator.validateAndCanonicalize(doc)).toThrow(GraphValidationError);
  });
});
