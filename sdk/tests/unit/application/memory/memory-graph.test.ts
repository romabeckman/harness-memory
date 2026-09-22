import { describe, expect, it } from "vitest";
import { MemoryGraph } from "../../../../src/application/memory/memory-graph.js";

describe("MemoryGraph", () => {
  const content = "# Orders\nREQUIRED: Reject empty orders.\n";
  const file = { path: "docs/feature/orders.md", content, sha256: "source-hash" };
  it("preserves full source documents and extracts cited rules into the original graph", () => {
    const graph = new MemoryGraph().seed([file], "commit-1");
    expect(graph.entities.find(e => e.type === "feature")?.metadata?.content).toBe(content);
    expect(graph.entities.find(e => e.type === "rule")?.metadata?.statement).toBe("Reject empty orders.");
    expect(graph.relations.some(r => r.type === "defines")).toBe(true);
    expect(graph.evidence[0].source).toBe(file.path);
    expect(graph).not.toHaveProperty("project_memory");
  });
  it("archives exact input text when the model improves a document", () => {
    const memory = new MemoryGraph();
    const seed = memory.seed([file], "commit-1");
    const proposed = structuredClone(seed);
    proposed.entities.find(e => e.type === "feature")!.metadata!.content = content + "## CONTEXT\nOrders API.\n";
    const graph = memory.reconcile(proposed, seed, undefined);
    expect(graph.entities.some(e => e.type === "document_revision" && e.metadata?.content === content)).toBe(true);
    expect(graph.relations.some(r => r.type === "supersedes")).toBe(true);
  });
  it("keeps prior memory when omitted and records explicit removal without losing content", () => {
    const memory = new MemoryGraph();
    const seed = memory.seed([file], "commit-1");
    const empty = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const retained = memory.reconcile(empty, empty, seed);
    expect(retained.entities.find(e => e.type === "feature")?.metadata?.content).toBe(content);
    const removed = structuredClone(seed);
    removed.entities.find(e => e.type === "feature")!.metadata!.lifecycle = "removed";
    const result = memory.reconcile(removed, empty, seed);
    expect(result.entities.find(e => e.type === "feature")?.metadata?.change).toBe("removed");
  });
});
