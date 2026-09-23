import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { MissingDocsMemoryService } from "../../../../src/application/memory/missing-docs-memory-service.js";
import { LocalDocsStore } from "../../../../src/infrastructure/memory/local-docs-store.js";
import { LocalTemporaryDocsWorkspace } from "../../../../src/infrastructure/memory/local-temporary-docs-workspace.js";

const document = (key: string, type: string, path: string, content: string) =>
  ({ key, type, name: key, metadata: { path, content } });
const generated = () => ({ schema_version: "1.0", entities: [
  document("adr:architecture", "adr", "docs/adr/ARCHITECTURE.md",
    "---\nnode_id: \"adr:architecture\"\n---\n# Architecture\n"),
  document("adr:tests", "adr", "docs/adr/TESTS.md",
    "---\nnode_id: \"adr:tests\"\n---\n# Tests\n"),
  document("feature:send", "feature", "docs/feature/send.md",
    "---\nnode_id: \"feature:send\"\n---\n# Send\n```graph\n{}\n```\n"),
  document("document:digest", "document", "docs/.digest.md", "# Digest\n"),
  document("document:index", "document", "docs/README.md", "# Index\n"),
], relations: [], evidence: [] });

describe("missing documentation staging", () => {
  it("creates physical .docs documents, processes them, promotes docs, and removes staging", async () => {
    const repository = mkdtempSync(join(tmpdir(), "harness-memory-bootstrap-"));
    try {
      const docs = new LocalDocsStore();
      const graph = generated();
      const bootstrap = { run: vi.fn().mockResolvedValue(graph) };
      const existing = { run: vi.fn().mockImplementation(async options => {
        expect(options.repository).toContain(join(repository, ".docs"));
        expect(readFileSync(join(options.repository, "docs/feature/send.md"), "utf8"))
          .toContain("# Send");
        expect(existsSync(join(repository, "docs"))).toBe(false);
        return graph;
      }) };
      const service = new MissingDocsMemoryService(
        bootstrap, existing, docs, new LocalTemporaryDocsWorkspace(),
      );
      const options = { repository, projectKey: "send", environment: "production",
        deploymentId: "d1", version: "1", agent: "codex-cli" as const, model: "test",
        effort: "low" as const, headRef: "HEAD", dryRun: false,
        apiUrl: "https://example.test", token: "secret" };

      await service.run(options, { commitSha: "a".repeat(40), headRef: "HEAD", files: [], diffs: [] });

      expect(existing.run).toHaveBeenCalledOnce();
      expect(existsSync(join(repository, "docs/feature/send.md"))).toBe(true);
      expect(existsSync(join(repository, "docs/.graph.json"))).toBe(true);
      expect(existsSync(join(repository, ".docs"))).toBe(false);
    } finally {
      rmSync(repository, { recursive: true, force: true });
    }
  });
});
