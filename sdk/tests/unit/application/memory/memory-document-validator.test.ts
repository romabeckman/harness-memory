import { describe, expect, it } from "vitest";
import { MemoryDocumentValidator } from "../../../../src/application/memory/memory-document-validator.js";
import type { GraphDocument } from "../../../../src/domain/contracts.js";

const document = (key: string, type: "adr" | "feature" | "document", path: string) => ({
  key, type, metadata: { path, content: "# Complete document\n" },
});

const graph = (): GraphDocument => ({
  schema_version: "1.0",
  entities: [
    document("adr:architecture", "adr", "docs/adr/ARCHITECTURE.md"),
    document("adr:tests", "adr", "docs/adr/TESTS.md"),
    document("document:digest", "document", "docs/.digest.md"),
    document("document:index", "document", "docs/README.md"),
    document("feature:orders", "feature", "docs/feature/orders.md"),
  ],
  relations: [], evidence: [],
});

describe("MemoryDocumentValidator", () => {
  const validator = new MemoryDocumentValidator();

  it("adds provenance only to changed documents", () => {
    const candidate = graph();
    const files = [{ path: "docs/adr/ARCHITECTURE.md", content: "# Complete document\n", sha256: "hash" }];

    validator.validateAndEnrich(candidate, files, "commit-123");

    expect(candidate.entities[0].metadata?.source_commit_sha).toBe("commit-123");
    expect(candidate.entities[0].metadata?.generated_by).toBeUndefined();
    expect(candidate.entities[1].metadata?.generated_by).toBe("harness-memory-sdk");
  });

  it("rejects duplicate document paths", () => {
    const candidate = graph();
    candidate.entities.push(document("feature:duplicate", "feature", "docs/feature/orders.md"));
    expect(() => validator.validateAndEnrich(candidate, [], "commit-123"))
      .toThrow("Duplicate document path: docs/feature/orders.md");
  });
});
