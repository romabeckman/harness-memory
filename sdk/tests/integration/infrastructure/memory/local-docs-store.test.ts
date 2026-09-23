import { afterEach, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { LocalDocsStore } from "../../../../src/infrastructure/memory/local-docs-store.js";

const roots: string[] = [];
afterEach(() => { for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true }); });
const repository = () => { const root = mkdtempSync(join(tmpdir(), "memory-docs-test-")); roots.push(root); return root; };

describe("LocalDocsStore", () => {
  it("reads untracked features and exact document content", () => {
    const root = repository();
    mkdirSync(join(root, "docs/feature"), { recursive: true });
    writeFileSync(join(root, "docs/feature/orders.md"), "# Orders\r\nFull context.\r\n");
    const files = new LocalDocsStore().read(root);
    expect(files[0].content).toBe("# Orders\r\nFull context.\r\n");
  });
  it("collects only project-memory documents and the graph index", () => {
    const root = repository();
    for (const folder of ["adr", "feature", "specs"]) mkdirSync(join(root, "docs", folder), { recursive: true });
    for (const path of ["adr/ARCHITECTURE.md", "feature/orders.md", "specs/plan.md",
      ".digest.md", ".graph.json", "README.md", "BUSINESS.md"]) {
      writeFileSync(join(root, "docs", path), path);
    }

    const paths = new LocalDocsStore().read(root).map(file => file.path).sort();

    expect(paths).toEqual(["docs/.digest.md", "docs/.graph.json",
      "docs/adr/ARCHITECTURE.md", "docs/feature/orders.md"]);
  });
});
