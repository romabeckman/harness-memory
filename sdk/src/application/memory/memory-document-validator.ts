import type { GraphDocument } from "../../domain/contracts.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import { DOCUMENT_TYPES, isMemoryPath } from "./memory-graph.js";

const REQUIRED_DOCUMENTS = [
  "docs/adr/ARCHITECTURE.md", "docs/adr/TESTS.md", "docs/.digest.md", "docs/README.md",
];

export class MemoryDocumentValidator {
  public validateAndEnrich(graph: GraphDocument, commitSha: string): void {
    const paths = new Set<string>();

    for (const entity of graph.entities.filter(item => DOCUMENT_TYPES.has(item.type))) {
      const path = entity.metadata?.path;
      if (typeof path !== "string" || !isMemoryPath(path) || path === "docs/.graph.json") {
        throw new GraphValidationError(`Invalid document path for '${entity.key}'`);
      }
      if (paths.has(path)) throw new GraphValidationError(`Duplicate document path: ${path}`);
      const metadata = entity.metadata;
      const content = metadata?.content;
      if (!metadata || typeof content !== "string" || !content.trim()) {
        throw new GraphValidationError(`Empty document: ${path}`);
      }
      paths.add(path);
      metadata.source_commit_sha = commitSha;
    }

    for (const path of REQUIRED_DOCUMENTS) {
      if (!paths.has(path)) throw new GraphValidationError(`Documentation graph must include ${path}`);
    }
    if (!graph.entities.some(entity => entity.type === "feature" && entity.metadata?.lifecycle !== "removed")) {
      throw new GraphValidationError("Documentation must describe at least one project feature");
    }
    this.validateRules(graph);
  }

  private validateRules(graph: GraphDocument): void {
    for (const rule of graph.entities.filter(entity => entity.type === "rule")) {
      if (typeof rule.metadata?.statement !== "string" || !rule.metadata.statement.trim()) {
        throw new GraphValidationError(`Rule '${rule.key}' needs its complete statement`);
      }
      const defines = graph.relations.find(relation =>
        relation.type === "defines" && relation.target_entity_key === rule.key);
      if (!defines || !graph.evidence.some(evidence => evidence.relation_ref === defines.ref)) {
        throw new GraphValidationError(`Rule '${rule.key}' needs document scope and evidence`);
      }
    }
  }
}
