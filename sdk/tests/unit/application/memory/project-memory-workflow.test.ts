import { describe, expect, it, vi } from "vitest";
import { ProjectMemoryWorkflow } from "../../../../src/application/memory/project-memory-workflow.js";
import { LlmExecutionError } from "../../../../src/domain/llm-execution-error.js";
import { GraphValidator } from "../../../../src/infrastructure/validator/graph-validator.js";

const options = { repository: "/repo", projectKey: "demo", environment: "production", deploymentId: "d1", version: "1", agent: "codex-cli" as const, model: "test", effort: "high" as const, headRef: "HEAD", dryRun: false, apiUrl: "https://example.test", token: "secret" };
const context = { commitSha: "a".repeat(40), headRef: "HEAD", files: [], diffs: [] };
const generated = () => ({ schema_version: "1.0", entities: [
  ["adr:architecture", "adr", "docs/adr/ARCHITECTURE.md"],
  ["adr:tests", "adr", "docs/adr/TESTS.md"],
  ["document:digest", "document", "docs/.digest.md"],
  ["feature:orders", "feature", "docs/feature/orders.md"],
].map(([key, type, path]) => ({ key, type, name: key, metadata: { path, content: "# Complete document\nProject context.\n" } })), relations: [], evidence: [] });
const completeFiles = () => [
  { path: "docs/.graph.json", content: JSON.stringify({ nodes: generated().entities.map(entity => ({
    path: entity.metadata.path, id: entity.key,
  })), edges: [] }), sha256: "sha" },
  ...generated().entities.map(entity => ({ path: entity.metadata.path,
    content: entity.metadata.path.startsWith("docs/adr/") || entity.metadata.path.startsWith("docs/feature/")
      ? `---\nnode_id: ${entity.key}\n---\n${entity.type === "feature" ? "```graph\n{}\n```\n" : ""}# Complete document\nProject context.\n`
      : "# Complete document\nProject context.\n", sha256: "sha" })),
  { path: "docs/README.md", content: "# Index", sha256: "sha" },
];

describe("ProjectMemoryWorkflow", () => {
  it("compares complete local docs with the latest graph without sending source files to the prompt", async () => {
    const previous = generated();
    const localFiles = previous.entities.map(entity => ({
      path: entity.metadata.path,
      content: entity.metadata.path === "docs/.digest.md" || entity.metadata.path === "docs/README.md"
        ? entity.metadata.content
        : `---\ndoc_type: ${entity.type}\nnode_id: ${entity.key}\n---\n${entity.type === "feature" ? '```graph\n{"node_id":"feature:orders"}\n```\n' : ""}${entity.metadata.content}`,
      sha256: "sha",
    }));
    localFiles.push({ path: "docs/README.md", content: "# Index", sha256: "sha" });
    localFiles.push({ path: "docs/.graph.json", content: JSON.stringify({ nodes: previous.entities.map(entity => ({
      path: entity.metadata.path, id: entity.key,
    })), edges: [] }), sha256: "sha" });
    const docs = { read: vi.fn().mockReturnValue(localFiles) };
    const llm = { run: vi.fn().mockResolvedValue(generated()) };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn().mockResolvedValue(previous) }, docs, new GraphValidator());
    const graph = await workflow.run(options, { ...context, files: [{ path: "src/orders.ts", content: "secret source", sha256: "sha" }], });
    const invocation = llm.run.mock.calls[0][0];
    expect(invocation.baselineGraph).toEqual(previous);
    expect(invocation.documentationGraph.entities).toHaveLength(4);
    expect(invocation.context.files).toEqual([]);
    expect(invocation.instruction).toContain("compare current documents with the latest published graph");
    expect(graph.entities.find(entity => entity.key === "feature:orders")?.metadata?.content)
      .toBe(localFiles.find(file => file.path === "docs/feature/orders.md")?.content);
  });
  it("fetches baseline before prompting", async () => {
    const previous = generated();
    const baseline = { load: vi.fn().mockResolvedValue(previous) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const llm = { run: vi.fn().mockResolvedValue(generated()) };
    const workflow = new ProjectMemoryWorkflow(llm, baseline, docs, new GraphValidator());
    const graph = await workflow.run(options, context);
    expect(baseline.load).toHaveBeenCalledWith(options.apiUrl, options.token, "demo", "production");
    expect(llm.run.mock.calls[0][0].baselineGraph.entities).toHaveLength(4);
    expect(llm.run.mock.calls[0][0].instruction).toContain("Preserve stable entity keys");
    expect(JSON.stringify(llm.run.mock.calls[0][0])).not.toContain('"token"');
    expect(graph).not.toHaveProperty("project_memory");
  });
  it("accepts legacy baselines containing rule and README entities", async () => {
    const previous = generated() as any;
    previous.entities.push({ key: "rule:old", type: "rule", metadata: { path: "docs/feature/orders.md", statement: "Old" } });
    previous.entities.push({ key: "document:index", type: "document", metadata: { path: "docs/README.md", content: "# Index" } });
    previous.relations.push({ ref: "old-rule", source_entity_key: "feature:orders", target_entity_key: "rule:old", type: "defines", provenance: "declared" });
    previous.evidence.push({ source: "docs/feature/orders.md", relation_ref: "old-rule" });
    const workflow = new ProjectMemoryWorkflow({ run: vi.fn().mockResolvedValue(generated()) },
      { load: vi.fn().mockResolvedValue(previous) }, { read: vi.fn().mockReturnValue(completeFiles()) }, new GraphValidator());

    const graph = await workflow.run(options, context);

    expect(graph.entities.some(entity => ["rule:old", "document:index"].includes(entity.key))).toBe(false);
    expect(graph.relations.some(relation => relation.ref === "old-rule")).toBe(false);
  });
  it("publishes the exact local graph index as snapshot metadata", async () => {
    const files = completeFiles();
    const docs = { read: vi.fn().mockReturnValue(files) };
    const workflow = new ProjectMemoryWorkflow({ run: vi.fn().mockResolvedValue(generated()) },
      { load: vi.fn().mockResolvedValue(undefined) }, docs, new GraphValidator());

    const graph = await workflow.run(options, context);

    expect((graph as any).metadata).toEqual(JSON.parse(files[0].content));
    expect(graph.entities.some(entity => entity.metadata?.path === "docs/.graph.json")).toBe(false);
  });
  it("rejects missing docs before loading a baseline or calling the model", async () => {
    const docs = { read: vi.fn().mockReturnValue([]) };
    const llm = { run: vi.fn() };
    const baseline = { load: vi.fn() };
    const workflow = new ProjectMemoryWorkflow(llm, baseline, docs, new GraphValidator());
    await expect(workflow.run(options, context)).rejects.toThrow("Existing documentation is incomplete");
    expect(baseline.load).not.toHaveBeenCalled();
    expect(llm.run).not.toHaveBeenCalled();
  });
  it("derives a missing entity key from its path without retrying the model", async () => {
    const graphWithoutKey = generated();
    graphWithoutKey.entities.push({ key: undefined, type: "document_revision", name: "Orders",
      metadata: { path: "src/orders.ts" } });
    const llm = { run: vi.fn().mockResolvedValue(graphWithoutKey) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    expect(graph.entities.some(entity => entity.key === "src-orders.ts")).toBe(false);
    expect(llm.run).toHaveBeenCalledTimes(1);
  });
  it("adds a stable hash suffix when a path-derived entity key collides", async () => {
    const graphWithCollision = generated();
    graphWithCollision.entities.push({ key: undefined, type: "document_revision", name: "Orders",
      metadata: { path: "src/orders.ts" } });
    graphWithCollision.entities.push({ key: "src-orders.ts", type: "document_revision", name: "Existing revision" });
    const llm = { run: vi.fn().mockResolvedValue(graphWithCollision) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    expect(graph.entities.some(entity => entity.metadata?.path === "src/orders.ts")).toBe(false);
    expect(new Set(graph.entities.map(entity => entity.key)).size).toBe(graph.entities.length);
    expect(llm.run).toHaveBeenCalledTimes(1);
  });
  it("retries once when the generated graph has an entity without a key", async () => {
    const invalid = { schema_version: "1.0", entities: [{ type: "document_revision", name: "Payments" }], relations: [], evidence: [] };
    const llm = { run: vi.fn().mockResolvedValueOnce(invalid).mockResolvedValueOnce(generated()) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const debug = vi.fn();
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator(), debug);

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    expect(graph.entities.some(entity => entity.key === "feature:orders")).toBe(true);
    expect(llm.run).toHaveBeenCalledTimes(2);
    expect(llm.run.mock.calls[1][0].instruction).toContain("entity at index 0");
    expect(llm.run.mock.calls[1][0].instruction).toContain("non-empty unique string key");
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("entities[0]"));
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("path=<none>"));
  });
  it("fails if the graph still has a missing key after one retry", async () => {
    const invalid = { schema_version: "1.0", entities: [{ type: "document_revision", name: "Payments" }], relations: [], evidence: [] };
    const llm = { run: vi.fn().mockResolvedValue(invalid) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toThrow("entity key is required");

    expect(llm.run).toHaveBeenCalledTimes(2);
  });
  it("retries a prose response with explicit JSON-only and no-file-write instructions", async () => {
    const llm = { run: vi.fn()
      .mockRejectedValueOnce(new LlmExecutionError("LLM output is not valid JSON: Unexpected token 'I'"))
      .mockResolvedValueOnce(generated()) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const debug = vi.fn();
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator(), debug);

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    expect(graph.entities.some(entity => entity.key === "feature:orders")).toBe(true);
    expect(llm.run).toHaveBeenCalledTimes(2);
    expect(llm.run.mock.calls[0][0].instruction).toContain("Do not call tools, read or write workspace files");
    expect(llm.run.mock.calls[0][0].instruction).toContain("SDK publishes graph data without writing documentation files");
    expect(llm.run.mock.calls[1][0].instruction).toContain("previous response was not valid JSON");
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("retrying graph synthesis"));
  });
  it("stops after one retry when the model returns prose again", async () => {
    const error = new LlmExecutionError("LLM output is not valid JSON: Unexpected token 'I'");
    const llm = { run: vi.fn().mockRejectedValue(error) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toBe(error);

    expect(llm.run).toHaveBeenCalledTimes(2);
  });
  it("does not retry unrelated model execution errors", async () => {
    const error = new LlmExecutionError("LLM timed out after 600 seconds");
    const llm = { run: vi.fn().mockRejectedValue(error) };
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toBe(error);

    expect(llm.run).toHaveBeenCalledTimes(1);
  });
  it("identifies a local seed entity without a key in debug output", async () => {
    const files = completeFiles();
    files[0].content = JSON.stringify({ nodes: [{ path: "docs/feature/orders.md", id: "" }], edges: [] });
    const docs = { read: vi.fn().mockReturnValue(files) };
    const llm = { run: vi.fn() };
    const debug = vi.fn();
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator(), debug);

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toThrow("entity key is required");

    expect(debug).toHaveBeenCalledWith(expect.stringContaining("seed missing key at entities["));
    expect(debug).toHaveBeenCalledWith(expect.stringContaining('path="docs/feature/orders.md"'));
    expect(llm.run).not.toHaveBeenCalled();
  });
  it("dry run validates documented memory", async () => {
    const docs = { read: vi.fn().mockReturnValue(completeFiles()) };
    const workflow = new ProjectMemoryWorkflow({ run: vi.fn().mockResolvedValue(generated()) }, { load: vi.fn() }, docs, new GraphValidator());
    await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);
  });
});
