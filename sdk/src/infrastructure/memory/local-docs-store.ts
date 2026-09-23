import { existsSync, lstatSync, readFileSync, readdirSync, realpathSync } from "node:fs";
import { join, resolve } from "node:path";
import { DocsStorePort } from "../../application/ports/docs-store.port.js";
import { CollectedFile } from "../../application/ports/git-context-collector.port.js";
import { digest, isMemoryPath } from "../../application/memory/memory-graph.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";

export class LocalDocsStore implements DocsStorePort {
  read(repository: string): CollectedFile[] {
    const root = realpathSync(repository);
    const files: CollectedFile[] = [];
    let bytes = 0;
    const visit = (path: string): void => {
      const full = this.safePath(root, path);
      if (!existsSync(full)) return;
      const stat = lstatSync(full);
      if (stat.isDirectory()) {
        for (const entry of readdirSync(full).sort()) {
          if (path === "docs" && !["adr", "feature", "specs", ".digest.md", ".graph.json", "README.md", "BUSINESS.md"].includes(entry)) continue;
          visit(`${path}/${entry}`);
        }
      } else if (stat.isFile() && isMemoryPath(path)) {
        bytes += stat.size;
        if (bytes > 10 * 1024 * 1024 || files.length >= 2000) throw new ContextCollectionError("Local documentation exceeds collection limits");
        const buffer = readFileSync(full);
        if (buffer.includes(0)) throw new ContextCollectionError(`Non-text documentation: ${path}`);
        const content = new TextDecoder("utf-8", { fatal: true }).decode(buffer);
        files.push({ path, content, sha256: digest(content) });
      }
    };
    visit("docs");
    return files;
  }

  private safePath(root: string, path: string): string {
    if (path !== "docs" && !isMemoryPath(path) && !/^docs\/(adr|feature|specs)(\/[\w. -]+)*$/.test(path)) throw new ContextCollectionError(`Unsafe documentation path: ${path}`);
    let current = root;
    for (const part of path.split("/")) {
      if (["..", ".", ""].includes(part)) throw new ContextCollectionError("Unsafe documentation path");
      current = join(current, part);
      try {
        if (lstatSync(current).isSymbolicLink()) throw new ContextCollectionError(`Symlink documentation path: ${path}`);
      } catch (error: any) { if (error.code !== "ENOENT") throw error; }
    }
    return resolve(root, path);
  }
}
