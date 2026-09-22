import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, realpathSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { randomUUID } from "node:crypto";
import { DocsStorePort } from "../../application/ports/docs-store.port.js";
import { CollectedFile } from "../../application/ports/git-context-collector.port.js";
import { digest, DOCUMENT_TYPES, isMemoryPath } from "../../application/memory/memory-graph.js";
import { GraphDocument } from "../../domain/contracts.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";
import { DocumentContentCodec } from "../../application/memory/document-content-codec.js";

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

  write(repository: string, graph: GraphDocument, originals: CollectedFile[]): void {
    graph = new DocumentContentCodec().decode(graph);
    const root = realpathSync(repository);
    const documents = graph.entities.filter(e => DOCUMENT_TYPES.has(e.type) && e.metadata?.lifecycle !== "removed");
    const targets = new Map<string, string>();
    for (const document of documents) {
      const { path, content } = document.metadata ?? {};
      if (typeof path !== "string" || !isMemoryPath(path) || typeof content !== "string") throw new ContextCollectionError("Invalid generated document path or content");
      if (targets.has(path)) throw new ContextCollectionError(`Duplicate document path: ${path}`);
      targets.set(path, content);
    }
    const keys = new Set(documents.map(d => d.key));
    const topology = {
      nodes: documents.filter(d => ["adr", "feature", "spec"].includes(d.type)).map(d => ({ id: d.key, type: d.type, title: d.name ?? d.key, path: d.metadata!.path, tags: d.metadata!.tags ?? [],
        ...(d.metadata!.related_docs ? { related_docs: d.metadata!.related_docs } : {}) })).sort((a, b) => a.id.localeCompare(b.id)),
      edges: graph.relations.filter(r => keys.has(r.source_entity_key) && keys.has(r.target_entity_key) && ["implements", "depends_on", "tested_by", "references", "child_of"].includes(r.type))
        .map(r => ({ source: r.source_entity_key, target: r.target_entity_key, relation: r.type })),
    };
    const indexed = new Set(topology.nodes.map(n => n.id));
    topology.edges = topology.edges.filter(e => indexed.has(e.source) && indexed.has(e.target))
      .sort((a, b) => `${a.source}|${a.relation}|${a.target}`.localeCompare(`${b.source}|${b.relation}|${b.target}`));
    targets.set("docs/.graph.json", JSON.stringify(topology));
    const before = new Map<string, string | undefined>();
    for (const [path] of targets) {
      const full = this.safePath(root, path);
      const current = existsSync(full) ? readFileSync(full, "utf8") : undefined;
      const original = originals.find(f => f.path === path);
      if (current !== original?.content) throw new ContextCollectionError(`Document changed since collection: ${path}`);
      before.set(path, current);
    }
    const written: string[] = [];
    try {
      for (const [path, content] of targets) {
        const full = this.safePath(root, path);
        const current = existsSync(full) ? readFileSync(full, "utf8") : undefined;
        if (current !== before.get(path)) throw new ContextCollectionError(`Document changed during write: ${path}`);
        if (current === content) continue;
        this.atomicWrite(full, content);
        written.push(path);
      }
    } catch (error) {
      for (const path of written.reverse()) {
        const full = this.safePath(root, path);
        if (readFileSync(full, "utf8") !== targets.get(path)) continue;
        const prior = before.get(path);
        if (prior === undefined) unlinkSync(full); else this.atomicWrite(full, prior);
      }
      throw error;
    }
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

  private atomicWrite(path: string, content: string): void {
    mkdirSync(dirname(path), { recursive: true });
    const temporary = `${path}.${randomUUID()}.tmp`;
    try { writeFileSync(temporary, content, { encoding: "utf8", flag: "wx" }); renameSync(temporary, path); }
    finally { if (existsSync(temporary)) unlinkSync(temporary); }
  }
}
