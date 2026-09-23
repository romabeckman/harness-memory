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
  ["document:index", "document", "docs/README.md"],
  ["feature:orders", "feature", "docs/feature/orders.md"],
].map(([key, type, path]) => ({ key, type, name: key, metadata: { path, content: "# Complete document\nProject context.\n" } })), relations: [], evidence: [] });

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
    localFiles.push({ path: "docs/.graph.json", content: JSON.stringify({ nodes: previous.entities.map(entity => ({
      path: entity.metadata.path, id: entity.key,
    })), edges: [] }), sha256: "sha" });
    const docs = { read: vi.fn().mockReturnValue(localFiles), write: vi.fn() };
    const llm = { run: vi.fn().mockResolvedValue(generated()) };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn().mockResolvedValue(previous) }, docs, new GraphValidator());
    const graph = await workflow.run(options, { ...context, files: [{ path: "src/orders.ts", content: "secret source", sha256: "sha" }], });
    const invocation = llm.run.mock.calls[0][0];
    expect(invocation.baselineGraph).toEqual(previous);
    expect(invocation.documentationGraph.entities).toHaveLength(5);
    expect(invocation.context.files).toEqual([]);
    expect(invocation.instruction).toContain("compare current documents with the latest published graph");
    expect(graph.entities.find(entity => entity.key === "feature:orders")?.metadata?.content)
      .toBe(localFiles.find(file => file.path === "docs/feature/orders.md")?.content);
  });
  it("fetches baseline before prompting and persists complete generated docs", async () => {
    const previous = generated();
    const baseline = { load: vi.fn().mockResolvedValue(previous) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const llm = { run: vi.fn().mockResolvedValue(generated()) };
    const workflow = new ProjectMemoryWorkflow(llm, baseline, docs, new GraphValidator());
    const graph = await workflow.run(options, context);
    expect(baseline.load).toHaveBeenCalledWith(options.apiUrl, options.token, "demo", "production");
    expect(llm.run.mock.calls[0][0].baselineGraph.entities).toHaveLength(5);
    expect(llm.run.mock.calls[0][0].instruction).toContain("Preserve stable entity keys");
    expect(JSON.stringify(llm.run.mock.calls[0][0])).not.toContain('"token"');
    expect(docs.write).toHaveBeenCalledWith("/repo", graph, []);
    expect(graph).not.toHaveProperty("project_memory");
  });
  it("fails bootstrap when model omits required documents", async () => {
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const workflow = new ProjectMemoryWorkflow({ run: vi.fn().mockResolvedValue({ schema_version: "1.0", entities: [], relations: [], evidence: [] }) }, { load: vi.fn().mockResolvedValue(undefined) }, docs, new GraphValidator());
    await expect(workflow.run(options, context)).rejects.toThrow(/ARCHITECTURE/);
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("derives a missing entity key from its path without retrying the model", async () => {
    const graphWithoutKey = generated();
    delete graphWithoutKey.entities.find(entity => entity.type === "feature")!.key;
    const llm = { run: vi.fn().mockResolvedValue(graphWithoutKey) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    expect(graph.entities.find(entity => entity.type === "feature")?.key).toBe("docs-feature-orders.md");
    expect(llm.run).toHaveBeenCalledTimes(1);
  });
  it("adds a stable hash suffix when a path-derived entity key collides", async () => {
    const graphWithCollision = generated();
    delete graphWithCollision.entities.find(entity => entity.type === "feature")!.key;
    graphWithCollision.entities.push({ key: "docs-feature-orders.md", type: "service", name: "Existing service" });
    const llm = { run: vi.fn().mockResolvedValue(graphWithCollision) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    const feature = graph.entities.find(entity => entity.type === "feature")!;
    expect(feature.key).toMatch(/^docs-feature-orders\.md-[a-f0-9]{12}$/);
    expect(graph.entities.some(entity => entity.type === "service" && entity.key === "docs-feature-orders.md")).toBe(true);
    expect(new Set(graph.entities.map(entity => entity.key)).size).toBe(graph.entities.length);
    expect(llm.run).toHaveBeenCalledTimes(1);
  });
  it("retries once when the generated graph has an entity without a key", async () => {
    const invalid = { schema_version: "1.0", entities: [{ type: "service", name: "Payments" }], relations: [], evidence: [] };
    const llm = { run: vi.fn().mockResolvedValueOnce(invalid).mockResolvedValueOnce(generated()) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const debug = vi.fn();
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator(), debug);

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    expect(graph.entities.some(entity => entity.key === "feature:orders")).toBe(true);
    expect(llm.run).toHaveBeenCalledTimes(2);
    expect(llm.run.mock.calls[1][0].instruction).toContain("entity at index 0");
    expect(llm.run.mock.calls[1][0].instruction).toContain("non-empty unique string key");
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("entities[0]"));
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("path=<none>"));
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("fails without writing if the graph still has a missing key after one retry", async () => {
    const invalid = { schema_version: "1.0", entities: [{ type: "service", name: "Payments" }], relations: [], evidence: [] };
    const llm = { run: vi.fn().mockResolvedValue(invalid) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toThrow("entity key is required");

    expect(llm.run).toHaveBeenCalledTimes(2);
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("retries a prose response with explicit JSON-only and no-file-write instructions", async () => {
    const llm = { run: vi.fn()
      .mockRejectedValueOnce(new LlmExecutionError("LLM output is not valid JSON: Unexpected token 'I'"))
      .mockResolvedValueOnce(generated()) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const debug = vi.fn();
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator(), debug);

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);

    expect(graph.entities.some(entity => entity.key === "feature:orders")).toBe(true);
    expect(llm.run).toHaveBeenCalledTimes(2);
    expect(llm.run.mock.calls[0][0].instruction).toContain("Do not call tools, read or write workspace files");
    expect(llm.run.mock.calls[0][0].instruction).toMatch(/SDK.*writes? (?:those )?files/i);
    expect(llm.run.mock.calls[1][0].instruction).toContain("previous response was not valid JSON");
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("retrying graph synthesis"));
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("stops after one retry when the model returns prose again", async () => {
    const error = new LlmExecutionError("LLM output is not valid JSON: Unexpected token 'I'");
    const llm = { run: vi.fn().mockRejectedValue(error) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toBe(error);

    expect(llm.run).toHaveBeenCalledTimes(2);
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("does not retry unrelated model execution errors", async () => {
    const error = new LlmExecutionError("LLM timed out after 600 seconds");
    const llm = { run: vi.fn().mockRejectedValue(error) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator());

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toBe(error);

    expect(llm.run).toHaveBeenCalledTimes(1);
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("identifies a local seed entity without a key in debug output", async () => {
    const files = [
      { path: "docs/.graph.json", content: JSON.stringify({ nodes: [{ path: "docs/README.md", id: "" }], edges: [] }), sha256: "sha" },
      { path: "docs/README.md", content: "# Index\n", sha256: "sha" },
    ];
    const docs = { read: vi.fn().mockReturnValue(files), write: vi.fn() };
    const llm = { run: vi.fn() };
    const debug = vi.fn();
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn() }, docs, new GraphValidator(), debug);

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context))
      .rejects.toThrow("entity key is required");

    expect(debug).toHaveBeenCalledWith(expect.stringContaining("seed missing key at entities[0]"));
    expect(debug).toHaveBeenCalledWith(expect.stringContaining('path="docs/README.md"'));
    expect(llm.run).not.toHaveBeenCalled();
  });
  it("dry run generates and validates without writing docs", async () => {
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const workflow = new ProjectMemoryWorkflow({ run: vi.fn().mockResolvedValue(generated()) }, { load: vi.fn() }, docs, new GraphValidator());
    await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, context);
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("processes every source file in bounded bootstrap batches when docs are missing", async () => {
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const summary = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const llm = { run: vi.fn().mockImplementation(async invocation =>
      invocation.instruction.includes("Summarize this source batch") ? summary : generated()) };
    const files = ["a.ts", "b.ts", "c.ts"].map(path => ({ path, sha256: "sha", content: "x".repeat(300_000) }));
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn().mockResolvedValue(undefined) }, docs, new GraphValidator());
    await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, { ...context, files });
    const batchCalls = llm.run.mock.calls.map(call => call[0]).filter(invocation =>
      invocation.instruction.includes("Summarize this source batch"));
    expect(batchCalls.length).toBeGreaterThan(1);
    expect(batchCalls.flatMap(invocation => invocation.context.files.map(file => file.path)).sort())
      .toEqual(files.map(file => file.path));
    expect(llm.run.mock.calls.at(-1)![0].context.files.every(file => file.content.length < 300_000)).toBe(true);
  });
  it("uses a source summary with an unkeyed concept as context for a valid final graph", async () => {
    const summary = { schema_version: "1.0", entities: [{ type: "service", name: "Send API" }], relations: [], evidence: [] };
    const llm = { run: vi.fn().mockImplementation(async invocation =>
      invocation.instruction.includes("Summarize this source batch") ? summary : generated()) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const debug = vi.fn();
    const files = ["src/a.ts", "src/b.ts", "src/c.ts"]
      .map(path => ({ path, sha256: "sha", content: "x".repeat(300_000) }));
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn().mockResolvedValue(undefined) }, docs, new GraphValidator(), debug);

    const graph = await workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, { ...context, files });

    const finalInvocation = llm.run.mock.calls.at(-1)![0];
    const sourceSummary = finalInvocation.context.files.find(file => file.path === ".harness-memory/source-summary-1.json");
    expect(JSON.parse(sourceSummary.content).entities[0]).toEqual({ type: "service", name: "Send API" });
    expect(graph.entities.some(entity => entity.key === "feature:orders")).toBe(true);
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("source batch 1/"));
    expect(docs.write).not.toHaveBeenCalled();
  });
  it("rejects a source summary without graph arrays before prompting for the final graph", async () => {
    const invalidSummary = { schema_version: "1.0", entities: {}, relations: [], evidence: [] };
    const llm = { run: vi.fn().mockResolvedValue(invalidSummary) };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const files = [{ path: "src/large.ts", sha256: "sha", content: "x".repeat(600_000) }];
    const workflow = new ProjectMemoryWorkflow(llm, { load: vi.fn().mockResolvedValue(undefined) }, docs, new GraphValidator());

    await expect(workflow.run({ ...options, apiUrl: undefined, token: undefined, dryRun: true }, { ...context, files }))
      .rejects.toThrow("entities must be an array");

    expect(llm.run).toHaveBeenCalledTimes(1);
    expect(docs.write).not.toHaveBeenCalled();
  });
});
