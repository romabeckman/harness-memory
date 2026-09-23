import { describe, expect, it, vi } from "vitest";
import { ProjectMemoryWorkflow } from "../../../../src/application/memory/project-memory-workflow.js";
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
});
