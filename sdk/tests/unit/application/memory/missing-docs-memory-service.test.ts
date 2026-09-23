import { describe, expect, it, vi } from "vitest";
import { MissingDocsMemoryService } from "../../../../src/application/memory/missing-docs-memory-service.js";

const options = { repository: "/repo", projectKey: "send", environment: "production",
  deploymentId: "d1", version: "1", agent: "codex-cli" as const, model: "test",
  effort: "low" as const, headRef: "HEAD", dryRun: false,
  apiUrl: "https://example.test", token: "secret" };
const context = { commitSha: "a".repeat(40), headRef: "HEAD", files: [], diffs: [] };
const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };

describe("MissingDocsMemoryService", () => {
  it("stages generated docs, processes them through the existing service, then promotes them", async () => {
    const stagedFiles = [{ path: "docs/.digest.md", content: "# Digest", sha256: "sha" }];
    const docs = { read: vi.fn().mockReturnValue(stagedFiles), write: vi.fn() };
    const bootstrap = { run: vi.fn().mockResolvedValue(graph) };
    const existing = { run: vi.fn().mockImplementation(async () => {
      expect(docs.write).toHaveBeenCalledWith("/repo/.docs/run-1", graph, []);
      return graph;
    }) };
    const workspace = { create: vi.fn().mockReturnValue("/repo/.docs/run-1"), cleanup: vi.fn() };
    const completeness = { isComplete: vi.fn().mockReturnValue(true) };
    const service = new MissingDocsMemoryService(bootstrap, existing, docs, workspace, completeness);

    expect(await service.run(options, context)).toBe(graph);

    expect(bootstrap.run).toHaveBeenCalledWith(expect.objectContaining({
      repository: "/repo/.docs/run-1", dryRun: true,
    }), context);
    expect(existing.run).toHaveBeenCalledWith(expect.objectContaining({
      repository: "/repo/.docs/run-1", dryRun: true,
    }), context);
    expect(docs.write).toHaveBeenNthCalledWith(2, "/repo", graph, []);
    expect(workspace.cleanup).toHaveBeenCalledWith("/repo/.docs/run-1");
  });

  it("keeps real docs absent during dry run and cleans staging on failure", async () => {
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const bootstrap = { run: vi.fn().mockResolvedValue(graph) };
    const existing = { run: vi.fn() };
    const workspace = { create: vi.fn().mockReturnValue("/repo/.docs/run-1"), cleanup: vi.fn() };
    const incomplete = { isComplete: vi.fn().mockReturnValue(false) };
    const service = new MissingDocsMemoryService(bootstrap, existing, docs, workspace, incomplete);

    await expect(service.run({ ...options, dryRun: true }, context))
      .rejects.toThrow("Bootstrap documentation is incomplete");

    expect(existing.run).not.toHaveBeenCalled();
    expect(docs.write).toHaveBeenCalledTimes(1);
    expect(workspace.cleanup).toHaveBeenCalledWith("/repo/.docs/run-1");
  });
});
