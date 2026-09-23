import { describe, expect, it, vi } from "vitest";
import { ExistingDocsMemoryService } from "../../../../src/application/memory/existing-docs-memory-service.js";

const options = { repository: "/repo", projectKey: "send", environment: "production",
  deploymentId: "d1", version: "1", agent: "codex-cli" as const, model: "test",
  effort: "low" as const, headRef: "HEAD", dryRun: true };
const context = { commitSha: "a".repeat(40), headRef: "HEAD", files: [], diffs: [] };

describe("ExistingDocsMemoryService", () => {
  it("processes only complete documentation through the existing workflow", async () => {
    const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const workflow = { run: vi.fn().mockResolvedValue(graph) };
    const docs = { read: vi.fn().mockReturnValue([{ path: "docs/.digest.md", content: "# Digest", sha256: "sha" }]),
      write: vi.fn() };
    const completeness = { isComplete: vi.fn().mockReturnValue(true) };
    const service = new ExistingDocsMemoryService(workflow, docs, completeness);

    expect(await service.run(options, context)).toBe(graph);
    expect(workflow.run).toHaveBeenCalledWith(options, context);
  });

  it("rejects an absent docs tree before invoking the existing workflow", async () => {
    const workflow = { run: vi.fn() };
    const docs = { read: vi.fn().mockReturnValue([]), write: vi.fn() };
    const service = new ExistingDocsMemoryService(workflow, docs);

    await expect(service.run(options, context)).rejects.toThrow("Existing documentation is incomplete");

    expect(workflow.run).not.toHaveBeenCalled();
  });
});
