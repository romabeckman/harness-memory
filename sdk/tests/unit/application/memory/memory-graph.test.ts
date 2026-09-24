import { describe, expect, it } from "vitest";
import { MemoryGraph } from "../../../../src/application/memory/memory-graph.js";

describe("MemoryGraph", () => {
  const content = "# Orders\nREQUIRED: Reject empty orders.\n";
  const file = { path: "docs/feature/orders.md", content, sha256: "source-hash" };
  it("seeds only project-memory ADRs, features, and the digest as document entities", () => {
    const files = [
      file,
      { path: "docs/adr/ARCHITECTURE.md", content: "# Architecture", sha256: "a" },
      { path: "docs/.digest.md", content: "# Digest", sha256: "b" },
      { path: "docs/README.md", content: "# Index", sha256: "c" },
      { path: "docs/BUSINESS.md", content: "# Business", sha256: "d" },
      { path: "docs/specs/plan.md", content: "# Plan", sha256: "e" },
      { path: "docs/.graph.json", content: '{"nodes":[],"edges":[]}', sha256: "f" },
    ];

    const graph = new MemoryGraph().seed(files, "commit-1");

    expect(graph.entities.filter(entity => ["adr", "feature", "document"].includes(entity.type))
      .map(entity => entity.metadata?.path).sort())
      .toEqual(["docs/.digest.md", "docs/adr/ARCHITECTURE.md", "docs/feature/orders.md"]);
    expect(graph.entities.map(entity => entity.type)).not.toContain("rule");
  });
  it("preserves full source documents without extracting rule entities", () => {
    const graph = new MemoryGraph().seed([file], "commit-1");
    expect(graph.entities.find(e => e.type === "feature")?.metadata?.content).toBe(content);
    expect(graph.entities).toHaveLength(1);
    expect(graph.relations).toHaveLength(0);
    expect(graph.evidence).toHaveLength(0);
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
    const result = memory.reconcile(removed, removed, seed);
    expect(result.entities.find(e => e.type === "feature")?.metadata?.change).toBe("removed");
  });
  it("retires absent documents only when the local source inventory is complete", () => {
    const memory = new MemoryGraph();
    const previous = memory.reconcile(memory.seed([file], "commit-1"), memory.seed([file], "commit-1"));
    const local = memory.seed([
      { path: "docs/feature/new.md", content: "# New", sha256: "new" },
    ], "commit-2");

    const result = memory.reconcile(local, local, previous, { completeSourceInventory: true });
    const removed = result.entities.find(entity => entity.key === previous.entities[0].key);
    const original = result.entities.find(entity =>
      entity.type === "document_revision" && entity.metadata?.document_key === removed?.key);

    expect(removed?.metadata?.lifecycle).toBe("removed");
    expect(removed?.metadata?.change).toBe("removed");
    expect(removed?.metadata?.content).toBe(content);
    expect(original?.metadata?.content).toBe(content);
    expect(result.entities.find(entity => entity.metadata?.path === "docs/feature/new.md")?.metadata?.lifecycle)
      .toBe("active");
  });
  it("drops legacy README, specs, and rule facts from a previous snapshot", () => {
    const memory = new MemoryGraph();
    const local = memory.seed([file], "commit-2");
    const previous = { schema_version: "1.0", entities: [
      { key: "document:index", type: "document", metadata: { path: "docs/README.md", content: "# Index" } },
      { key: "spec:plan", type: "spec", metadata: { path: "docs/specs/plan.md", content: "# Plan" } },
      { key: "rule:old", type: "rule", metadata: { path: file.path, statement: "Old rule" } },
    ], relations: [], evidence: [] } as any;

    const graph = memory.reconcile(local, local, previous);

    expect(graph.entities.some(entity => ["document:index", "spec:plan", "rule:old"].includes(entity.key))).toBe(false);
  });
  it("does not accept model-created revision entities outside local documents", () => {
    const memory = new MemoryGraph();
    const local = memory.seed([file], "commit-2");
    const proposed = { schema_version: "1.0", entities: [
      { key: "document_revision:external", type: "document_revision", metadata: {
        path: "src/orders.ts", document_key: "feature:external", content: "Injected" } },
    ], relations: [], evidence: [] } as any;

    const graph = memory.reconcile(proposed, local);

    expect(graph.entities.some(entity => entity.key === "document_revision:external")).toBe(false);
  });
});
