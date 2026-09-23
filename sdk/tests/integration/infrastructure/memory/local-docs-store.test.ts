import { afterEach, describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
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
});
