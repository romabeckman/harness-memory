import { describe, expect, it, vi } from "vitest";
import { GitContextCollector } from "../../../../src/infrastructure/git/git-context-collector.js";
import { ContextCollectionError } from "../../../../src/domain/context-collection-error.js";
import { realpathSync } from "node:fs";
import { resolve } from "node:path";

describe("GitContextCollector", () => {
  const collector = new GitContextCollector();

  it("fails closed when repository is not a valid git repo", async () => {
    await expect(
      collector.collect({
        repository: resolve("./non-existent-folder-12345"),
        headRef: "HEAD",
        maxFiles: 100,
        maxBytes: 10000,
      })
    ).rejects.toThrow(ContextCollectionError);
  });

  it("collects files and commit sha in a valid git repository", async () => {
    // Current working directory (repo root) is a git repository
    const result = await collector.collect({
      repository: resolve("../"),
      headRef: "HEAD",
      maxFiles: 5000,
      maxBytes: 50_000_000,
    });

    expect(result.commitSha).toHaveLength(40);
    expect(Array.isArray(result.files)).toBe(true);
    expect(result.files.length).toBeGreaterThan(0);
    // Ensure .git or node_modules or venv are excluded
    for (const f of result.files) {
      expect(f.path).not.toMatch(/node_modules/);
      expect(f.path).not.toMatch(/^\.git\//);
      expect(f.path).not.toMatch(/^venv/);
    }
  });

  it("fails closed when maxFiles limit is exceeded", async () => {
    await expect(
      collector.collect({
        repository: resolve("../"),
        headRef: "HEAD",
        maxFiles: 1, // artificially tiny
        maxBytes: 50_000_000,
      })
    ).rejects.toThrow(ContextCollectionError);
  });

  it("fails closed when maxBytes limit is exceeded before reading into memory (heap bounds)", async () => {
    await expect(
      collector.collect({
        repository: resolve("../"),
        headRef: "HEAD",
        maxFiles: 5000,
        maxBytes: 10, // tiny budget: any file exceeds 10 bytes
      })
    ).rejects.toThrow(/exceeds maxBytes limit/);
  });

  it("detects symlink escaping repository root and throws ContextCollectionError", async () => {
    const symlinkCollector = new GitContextCollector({
      realpathSync: ((p: any) => {
        const str = String(p);
        if (str.includes("README.md") || str.includes("package.json") || str.includes("LICENSE")) {
          return resolve("C:/outside-repo/secret.txt");
        }
        return realpathSync(p);
      }) as any,
    });

    await expect(
      symlinkCollector.collect({
        repository: resolve("../"),
        headRef: "HEAD",
        maxFiles: 5000,
        maxBytes: 50_000_000,
      })
    ).rejects.toThrow(/Symlink escape detected/);
  });
});

