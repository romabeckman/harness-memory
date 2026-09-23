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
  it("stores the first complete document as an original revision", () => {
    const memory = new MemoryGraph();
    const seed = memory.seed([file], "commit-1");
    const graph = memory.reconcile(seed, seed);
    const document = graph.entities.find(e => e.type === "feature")!;
    const original = graph.entities.find(e => e.type === "document_revision" && e.metadata?.version === "original");
    expect(original?.name).toBe(document.name);
    expect(original?.metadata?.content).toBe(content);
    expect(graph.relations.some(r => r.type === "supersedes" && r.source_entity_key === document.key && r.target_entity_key === original?.key)).toBe(true);
  });
  it("records changed lines with conflict markers in revision metadata only", () => {
    const memory = new MemoryGraph();
    const seed = memory.seed([file], "commit-1");
    const proposed = structuredClone(seed);
    proposed.entities.find(e => e.type === "feature")!.metadata!.content = "# Orders\nREQUIRED: Reject invalid orders.\n";
    const previous = memory.reconcile(seed, seed);
    const graph = memory.reconcile(proposed, proposed, previous);
    const changed = graph.entities.filter(e => e.type === "document_revision" && e.metadata?.version === "line");
    expect(changed).toHaveLength(1);
    expect(changed[0].metadata?.content).toBe("REQUIRED: Reject invalid orders.");
    expect(changed[0].metadata?.conflict_marker).toBe("<<<<<<< HEAD\nREQUIRED: Reject invalid orders.\n=======\nREQUIRED: Reject empty orders.\n>>>>>>> published-baseline");
    expect(proposed.entities.find(e => e.type === "feature")!.metadata!.content).not.toContain("<<<<<<<");
    expect(graph.entities.find(e => e.type === "document_revision" && e.metadata?.version === "original")?.metadata?.content).toBe(content);
    expect(graph.relations.filter(r => r.type === "supersedes")).toHaveLength(2);
  });
  it("tracks an inserted line without marking surrounding lines as changed", () => {
    const memory = new MemoryGraph();
    const initial = memory.seed([file], "commit-1");
    const previous = memory.reconcile(initial, initial);
    const current = structuredClone(initial);
    current.entities.find(e => e.type === "feature")!.metadata!.content = "# Orders\nNew line.\nREQUIRED: Reject empty orders.\n";
    const result = memory.reconcile(current, current, previous);
    const lines = result.entities.filter(e => e.type === "document_revision" && e.metadata?.version === "line");
    expect(lines).toHaveLength(1);
    expect(lines[0].metadata?.content).toBe("New line.");
    expect(lines[0].metadata?.change).toBe("added");
    const repeated = memory.reconcile(current, current, previous);
    expect(repeated.entities.filter(e => e.type === "document_revision").map(e => e.key))
      .toEqual(result.entities.filter(e => e.type === "document_revision").map(e => e.key));
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
