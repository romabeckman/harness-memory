import { afterEach, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { LocalDocsStore } from "../../../../src/infrastructure/memory/local-docs-store.js";

const roots: string[] = [];
afterEach(() => { for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true }); });
const repository = () => { const root = mkdtempSync(join(tmpdir(), "memory-docs-test-")); roots.push(root); return root; };

describe("LocalDocsStore", () => {
  it("reads untracked specs and exact document content", () => {
    const root = repository();
    mkdirSync(join(root, "docs/specs"), { recursive: true });
    writeFileSync(join(root, "docs/specs/orders.md"), "# Orders\r\nFull context.\r\n");
    const files = new LocalDocsStore().read(root);
    expect(files[0].content).toBe("# Orders\r\nFull context.\r\n");
  });
  it("rejects model path escapes before writing", () => {
    const root = repository();
    const graph = { schema_version: "1.0", entities: [{ key: "document:x", type: "document" as const, metadata: { path: "docs/../outside.md", content: "no" } }], relations: [], evidence: [] };
    expect(() => new LocalDocsStore().write(root, graph, [])).toThrow(/path/i);
  });
  it("does not overwrite edits made after collection", () => {
    const root = repository();
    mkdirSync(join(root, "docs/feature"), { recursive: true });
    const path = join(root, "docs/feature/orders.md");
    writeFileSync(path, "Original");
    const store = new LocalDocsStore();
    const files = store.read(root);
    writeFileSync(path, "Human edit");
    const graph = { schema_version: "1.0", entities: [{ key: "feature:orders", type: "feature" as const, metadata: { path: "docs/feature/orders.md", content: "Model edit" } }], relations: [], evidence: [] };
    expect(() => store.write(root, graph, files)).toThrow(/changed/i);
    expect(readFileSync(path, "utf8")).toBe("Human edit");
  });
});
