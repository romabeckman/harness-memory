import { createHash } from "node:crypto";
import { CollectedFile } from "../ports/git-context-collector.port.js";
import { ALLOWED_RELATION_TYPES, EntityFact, EntityType, GraphDocument, RelationFact, RelationType } from "../../domain/contracts.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";

export const DOCUMENT_TYPES = new Set<EntityType>(["adr", "feature", "document"]);
export const digest = (text: string): string => createHash("sha256").update(text, "utf8").digest("hex");
export const isMemoryPath = (path: string): boolean =>
  !path.includes("\\") && !path.split("/").some(p => p === ".." || p === "." || p === "") &&
  (/^docs\/(adr|feature)\/[\w./ -]+\.md$/i.test(path) ||
    ["docs/.digest.md", "docs/.graph.json"].includes(path));
const empty = (): GraphDocument => ({ schema_version: "1.0", entities: [], relations: [], evidence: [] });
const isPublishableDocumentPath = (path: unknown): path is string =>
  typeof path === "string" && isMemoryPath(path) && path !== "docs/.graph.json";
const memoryEntity = (e: EntityFact): boolean =>
  (DOCUMENT_TYPES.has(e.type) || e.type === "document_revision") && isPublishableDocumentPath(e.metadata?.path);

export class MemoryGraph {
  public seed(files: CollectedFile[], commit: string): GraphDocument {
    const graph = empty();
    const indexFile = files.find(f => f.path === "docs/.graph.json");
    const index = indexFile ? JSON.parse(indexFile.content) : { nodes: [], edges: [] };
    if (!index || typeof index !== "object" || Array.isArray(index) ||
        !Array.isArray(index.nodes) || !Array.isArray(index.edges)) {
      throw new GraphValidationError("Invalid docs/.graph.json topology");
    }
    graph.metadata = index;
    const indexed = new Map<string, any>();
    for (const node of index.nodes) {
      if (typeof node.path !== "string") throw new GraphValidationError("Invalid document path in docs/.graph.json");
      if (!isMemoryPath(node.path)) continue;
      indexed.set(node.path, node);
    }
    for (const file of files.filter(f => isMemoryPath(f.path) && f.path !== "docs/.graph.json")) {
      const node = indexed.get(file.path);
      const type: EntityType = file.path.startsWith("docs/adr/") ? "adr" : file.path.startsWith("docs/feature/") ? "feature" : "document";
      const frontmatterId = file.content.match(/^node_id:\s*["']?([^"'\r\n]+)["']?\s*$/m)?.[1]?.trim();
      const key = node?.id ?? frontmatterId ?? `${type}:${digest(file.path).slice(0, 24)}`;
      const title = node?.title ?? file.content.match(/^#\s+(.+)$/m)?.[1] ?? file.path;
      const micrograph = file.content.match(/```graph\s*\n([\s\S]*?)\n```/);
      const metadata: Record<string, unknown> = {
        path: file.path, content: file.content, content_sha256: digest(file.content),
        source_commit_sha: commit, tags: node?.tags ?? [], lifecycle: "active",
      };
      if (micrograph) metadata.context = JSON.parse(micrograph[1]);
      if (node?.related_docs) metadata.related_docs = node.related_docs;
      graph.entities.push({ key, type, name: title, metadata });
    }
    const keys = new Set(graph.entities.map(e => e.key));
    for (const edge of index.edges) {
      if (!keys.has(edge.source) || !keys.has(edge.target)) continue;
      if (!ALLOWED_RELATION_TYPES.includes(edge.relation)) throw new GraphValidationError("Unknown document relation");
      graph.relations.push(this.edge(edge.source, edge.relation, edge.target));
    }
    return graph;
  }

  public reconcile(
    _proposed: GraphDocument, local: GraphDocument, previous?: GraphDocument,
    options: { completeSourceInventory?: boolean } = {},
  ): GraphDocument {
    const entities = new Map<string, EntityFact>();
    const localDocumentKeys = new Set(local.entities.filter(entity => DOCUMENT_TYPES.has(entity.type)).map(entity => entity.key));
    for (const entity of previous?.entities.filter(memoryEntity) ?? []) {
      const retained = structuredClone(entity);
      if (options.completeSourceInventory && DOCUMENT_TYPES.has(retained.type) && !localDocumentKeys.has(retained.key)) {
        retained.metadata ??= {};
        retained.metadata.lifecycle = "removed";
      }
      entities.set(retained.key, retained);
    }
    for (const entity of local.entities) entities.set(entity.key, structuredClone(entity));
    const prior = new Map(previous?.entities.map(e => [e.key, e]) ?? []);
    const revisions: RelationFact[] = [];
    for (const entity of [...entities.values()].filter(item => DOCUMENT_TYPES.has(item.type))) {
      const currentContent = entity.metadata?.content;
      if (typeof currentContent !== "string") continue;
      const previousContent = prior.get(entity.key)?.metadata?.content;
      const originalExists = [...entities.values()].some(item =>
        item.type === "document_revision" && item.metadata?.document_key === entity.key && item.metadata?.version === "original");
      if (!originalExists) {
        const original = typeof previousContent === "string" ? previousContent : currentContent;
        const key = `document_revision:${digest(`${entity.key}|original|${original}`).slice(0, 40)}`;
        entities.set(key, { key, type: "document_revision", name: entity.name,
          metadata: { document_key: entity.key, path: entity.metadata?.path, version: "original",
            content: original, content_sha256: digest(original) } });
        revisions.push(this.edge(entity.key, "supersedes", key));
      }
      if (typeof previousContent !== "string" || previousContent === currentContent) continue;
      this.addLineRevisions(entity, previousContent, currentContent, entities, revisions);
    }
    for (const entity of entities.values()) {
      if (!memoryEntity(entity)) continue;
      entity.metadata ??= {};
      if (DOCUMENT_TYPES.has(entity.type) && typeof entity.metadata.content !== "string") {
        throw new GraphValidationError(`Document '${entity.key}' must retain complete content`);
      }
      if (typeof entity.metadata.content === "string") entity.metadata.content_sha256 = digest(entity.metadata.content);
      const old = prior.get(entity.key);
      const before = old?.metadata?.content ?? old?.metadata?.statement;
      const after = entity.metadata.content ?? entity.metadata.statement;
      entity.metadata.change = entity.metadata.lifecycle === "removed" ? "removed" : !old ? "added" : before === after ? "unchanged" : "modified";
      if (old && typeof before === "string") entity.metadata.previous_sha256 = digest(before);
    }
    const relations = new Map<string, RelationFact>();
    for (const relation of [...(previous?.relations ?? []), ...local.relations, ...revisions]) {
      if (entities.has(relation.source_entity_key) && entities.has(relation.target_entity_key)) relations.set(relation.ref, relation);
    }
    const evidence = [...(previous?.evidence ?? []), ...local.evidence]
      .filter(e => !e.relation_ref || relations.has(e.relation_ref));
    return { schema_version: "1.0", metadata: local.metadata, entities: [...entities.values()], relations: [...relations.values()],
      evidence: [...new Map(evidence.map(e => [JSON.stringify(e), e])).values()] };
  }

  private addLineRevisions(
    entity: EntityFact, before: string, after: string,
    entities: Map<string, EntityFact>, relations: RelationFact[],
  ): void {
    const oldLines = before.split(/\r?\n/);
    const newLines = after.split(/\r?\n/);
    const aligned = this.alignLines(oldLines, newLines);
    let oldIndex = 0;
    let newIndex = 0;
    let operation = 0;
    while (operation < aligned.length) {
      if (aligned[operation] === "equal") { oldIndex++; newIndex++; operation++; continue; }
      const removed: string[] = [];
      const added: string[] = [];
      while (operation < aligned.length && aligned[operation] !== "equal") {
        if (aligned[operation] === "removed") removed.push(oldLines[oldIndex++]);
        else added.push(newLines[newIndex++]);
        operation++;
      }
      for (let offset = 0; offset < Math.max(removed.length, added.length); offset++) {
        const oldLine = removed[offset];
        const newLine = added[offset];
        const line = newLine === undefined ? oldIndex - removed.length + offset + 1 : newIndex - added.length + offset + 1;
        this.addLineRevision(entity, before, after, oldLine, newLine, line, entities, relations);
      }
    }
  }

  private addLineRevision(
    entity: EntityFact, before: string, after: string, oldLine: string | undefined,
    newLine: string | undefined, line: number, entities: Map<string, EntityFact>, relations: RelationFact[],
  ): void {
      const content = newLine ?? oldLine ?? "";
      const key = `document_revision:${digest(`${entity.key}|${digest(before)}|${digest(after)}|${line}|${oldLine ?? ""}|${newLine ?? ""}`).slice(0, 40)}`;
      const marker = `<<<<<<< HEAD\n${newLine ?? ""}\n=======\n${oldLine ?? ""}\n>>>>>>> published-baseline`;
      entities.set(key, { key, type: "document_revision", name: entity.name,
        metadata: { document_key: entity.key, path: entity.metadata?.path, version: "line",
          line, content, change: newLine === undefined ? "removed" : oldLine === undefined ? "added" : "modified",
          conflict_marker: marker, source_commit_sha: entity.metadata?.source_commit_sha } });
      relations.push(this.edge(entity.key, "supersedes", key));
  }

  private alignLines(before: string[], after: string[]): Array<"equal" | "added" | "removed"> {
    const rows = before.length;
    const columns = after.length;
    if (rows * columns > 4_000_000) {
      throw new GraphValidationError("Document line diff exceeds 4,000,000 comparisons");
    }
    const lcs = Array.from({ length: rows + 1 }, () => new Uint32Array(columns + 1));
    for (let i = rows - 1; i >= 0; i--) {
      for (let j = columns - 1; j >= 0; j--) {
        lcs[i][j] = before[i] === after[j] ? 1 + lcs[i + 1][j + 1] : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
      }
    }
    const changes: Array<"equal" | "added" | "removed"> = [];
    let i = 0;
    let j = 0;
    while (i < rows || j < columns) {
      if (i < rows && j < columns && before[i] === after[j]) {
        changes.push("equal"); i++; j++;
      } else if (j < columns && (i === rows || lcs[i][j + 1] >= lcs[i + 1][j])) {
        changes.push("added"); j++;
      } else {
        changes.push("removed"); i++;
      }
    }
    return changes;
  }

  private edge(source: string, type: RelationType, target: string): RelationFact {
    return { ref: `memory:${digest(`${source}|${type}|${target}`).slice(0, 40)}`,
      source_entity_key: source, target_entity_key: target, type, provenance: "declared" };
  }
}
