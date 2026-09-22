import { createHash } from "node:crypto";
import { CollectedFile } from "../ports/git-context-collector.port.js";
import { ALLOWED_RELATION_TYPES, EntityFact, EntityType, GraphDocument, RelationFact, RelationType } from "../../domain/contracts.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";

export const DOCUMENT_TYPES = new Set<EntityType>(["adr", "feature", "spec", "document"]);
export const digest = (text: string): string => createHash("sha256").update(text, "utf8").digest("hex");
export const isMemoryPath = (path: string): boolean =>
  !path.includes("\\") && !path.split("/").some(p => p === ".." || p === "." || p === "") &&
  (/^docs\/(adr|feature|specs)\/[\w./ -]+\.md$/i.test(path) ||
    ["docs/.digest.md", "docs/.graph.json", "docs/README.md", "docs/BUSINESS.md"].includes(path));
const empty = (): GraphDocument => ({ schema_version: "1.0", entities: [], relations: [], evidence: [] });
const memoryEntity = (e: EntityFact): boolean => DOCUMENT_TYPES.has(e.type) || e.type === "rule" || e.type === "document_revision";

export class MemoryGraph {
  public seed(files: CollectedFile[], commit: string): GraphDocument {
    const graph = empty();
    const indexFile = files.find(f => f.path === "docs/.graph.json");
    const index = indexFile ? JSON.parse(indexFile.content) : { nodes: [], edges: [] };
    if (!Array.isArray(index.nodes) || !Array.isArray(index.edges)) throw new GraphValidationError("Invalid docs/.graph.json topology");
    const indexed = new Map<string, any>();
    for (const node of index.nodes) {
      if (typeof node.path !== "string" || !isMemoryPath(node.path)) throw new GraphValidationError("Invalid document path in docs/.graph.json");
      indexed.set(node.path, node);
    }
    for (const file of files.filter(f => isMemoryPath(f.path) && f.path !== "docs/.graph.json")) {
      const node = indexed.get(file.path);
      const type: EntityType = file.path.startsWith("docs/adr/") ? "adr" : file.path.startsWith("docs/feature/") ? "feature" : file.path.startsWith("docs/specs/") ? "spec" : "document";
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
      file.content.split(/\r?\n/).forEach((line, i) => {
        const rule = line.match(/^\s*(?:[-*]\s+)?(?:\*\*)?(REQUIRED|PROHIBITED|FORBIDDEN|ALLOWED):(?:\*\*)?\s*(.+)$/);
        if (!rule) return;
        const ruleKey = `rule:${digest(`${key}|${rule[1]}|${rule[2]}`).slice(0, 32)}`;
        if (graph.entities.some(e => e.key === ruleKey)) return;
        graph.entities.push({ key: ruleKey, type: "rule", name: rule[2].slice(0, 255), metadata: {
          statement: rule[2], modality: rule[1] === "FORBIDDEN" ? "PROHIBITED" : rule[1],
          document_key: key, path: file.path, line: i + 1, lifecycle: "active", source_commit_sha: commit,
        } });
        const relation = this.edge(key, "defines", ruleKey);
        graph.relations.push(relation);
        graph.evidence.push({ source: file.path, excerpt: line.slice(0, 4096), relation_ref: relation.ref,
          metadata: { line: i + 1, content_sha256: digest(file.content), source_commit_sha: commit } });
      });
    }
    const keys = new Set(graph.entities.map(e => e.key));
    for (const edge of index.edges) {
      if (!keys.has(edge.source) || !keys.has(edge.target)) continue;
      if (!ALLOWED_RELATION_TYPES.includes(edge.relation)) throw new GraphValidationError("Unknown document relation");
      graph.relations.push(this.edge(edge.source, edge.relation, edge.target));
    }
    return graph;
  }

  public reconcile(proposed: GraphDocument, local: GraphDocument, previous?: GraphDocument): GraphDocument {
    const entities = new Map<string, EntityFact>();
    for (const entity of previous?.entities.filter(memoryEntity) ?? []) entities.set(entity.key, structuredClone(entity));
    for (const entity of local.entities) entities.set(entity.key, structuredClone(entity));
    const archives: RelationFact[] = [];
    for (const entity of proposed.entities) {
      const original = entities.get(entity.key);
      if (original && DOCUMENT_TYPES.has(original.type) && typeof original.metadata?.content === "string" &&
          typeof entity.metadata?.content === "string" && original.metadata.content !== entity.metadata.content) {
        const archiveKey = `document_revision:${digest(original.key + original.metadata.content).slice(0, 32)}`;
        entities.set(archiveKey, { ...structuredClone(original), key: archiveKey, type: "document_revision",
          metadata: { ...original.metadata, document_key: original.key, lifecycle: "archived" } });
        archives.push(this.edge(entity.key, "supersedes", archiveKey));
      }
      entities.set(entity.key, structuredClone(entity));
    }
    const prior = new Map(previous?.entities.map(e => [e.key, e]) ?? []);
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
    for (const relation of [...(previous?.relations ?? []), ...local.relations, ...proposed.relations, ...archives]) {
      if (entities.has(relation.source_entity_key) && entities.has(relation.target_entity_key)) relations.set(relation.ref, relation);
    }
    const evidence = [...(previous?.evidence ?? []), ...local.evidence, ...proposed.evidence]
      .filter(e => !e.relation_ref || relations.has(e.relation_ref));
    return { schema_version: "1.0", entities: [...entities.values()], relations: [...relations.values()],
      evidence: [...new Map(evidence.map(e => [JSON.stringify(e), e])).values()] };
  }

  private edge(source: string, type: RelationType, target: string): RelationFact {
    return { ref: `memory:${digest(`${source}|${type}|${target}`).slice(0, 40)}`,
      source_entity_key: source, target_entity_key: target, type, provenance: "declared" };
  }
}
