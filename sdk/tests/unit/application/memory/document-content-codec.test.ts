import { expect, it } from "vitest";
import { DocumentContentCodec } from "../../../../src/application/memory/document-content-codec.js";
import { GraphValidator } from "../../../../src/infrastructure/validator/graph-validator.js";

it("stores and reconstructs large Unicode documents without exceeding graph metadata bounds", () => {
  const content = "Full feature context 😀\r\n".repeat(6000);
  const graph = { schema_version: "1.0", entities: [{ key: "feature:large", type: "feature" as const, metadata: { path: "docs/feature/large.md", content } }], relations: [], evidence: [] };
  const codec = new DocumentContentCodec();
  const encoded = codec.encode(graph);
  expect(() => new GraphValidator().validateAndCanonicalize(encoded)).not.toThrow();
  expect(encoded.entities.some(e => e.type === "document_section")).toBe(true);
  expect(codec.decode(encoded).entities[0].metadata?.content).toBe(content);
  expect(graph.entities[0].metadata.content).toBe(content);
});

it("rejects missing or corrupt stored document sections", () => {
  const codec = new DocumentContentCodec();
  const graph = codec.encode({ schema_version: "1.0", entities: [{ key: "spec:large", type: "spec", metadata: { content: "a".repeat(100000) } }], relations: [], evidence: [] });
  graph.entities.pop();
  expect(() => codec.decode(graph)).toThrow(/section/i);
});
