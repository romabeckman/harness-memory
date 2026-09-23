import { ALLOWED_ENTITY_TYPES, type GraphDocument, type PublishSnapshotOptions } from "../../domain/contracts.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";
import type { DocsStorePort } from "../ports/docs-store.port.js";
import type { CollectedFile, RepositoryContext } from "../ports/git-context-collector.port.js";
import type { GraphValidatorPort } from "../ports/graph-validator.port.js";
import type { LlmInvocationOptions, LlmRunnerPort } from "../ports/llm-runner.port.js";
import type { MemoryWorkflowOutcome, MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import type { PublicationBaselinePort } from "../ports/publication-baseline.port.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import { DocumentContentCodec } from "./document-content-codec.js";
import { MemoryDocumentValidator } from "./memory-document-validator.js";
import { DOCUMENT_TYPES, isMemoryPath, MemoryGraph } from "./memory-graph.js";
import { PROJECT_MEMORY_PROMPT } from "./project-memory-prompt.js";
import { ProjectMemoryCompleteness } from "./project-memory-completeness.js";
import { digest } from "./memory-graph.js";

const MAX_ENTITY_KEY_LENGTH = 255;
const ENTITY_KEY_HASH_LENGTH = 12;

export class ProjectMemoryWorkflow implements MemoryWorkflowPort {
  private readonly codec = new DocumentContentCodec();
  private readonly memory = new MemoryGraph();
  private readonly documentValidator = new MemoryDocumentValidator();
  private readonly completeness = new ProjectMemoryCompleteness();

  constructor(
    private readonly llm: LlmRunnerPort,
    private readonly baseline: PublicationBaselinePort,
    private readonly docs: DocsStorePort,
    private readonly validator: GraphValidatorPort,
    private readonly debug?: (message: string) => void,
  ) {}

  public async run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<MemoryWorkflowOutcome> {
    this.validatePublicationOptions(options);
    const files = this.docs.read(options.repository);
    if (!this.completeness.isComplete(files)) {
      throw new GraphValidationError("Existing documentation is incomplete");
    }
    this.validateContextBudget(files, options);
    this.debug?.("Memory: loading previous snapshot");
    const previous = await this.loadPrevious(options);
    this.debug?.(`Memory: previous snapshot ${previous ? `has ${previous.entities.length} entities` : "absent"}`);
    const seed = this.memory.seed(files, context.commitSha);
    this.debug?.(`Memory: local docs=${files.length}, seed entities=${seed.entities.length}`);
    this.reportMissingEntityKeys(seed, "seed");
    this.validator.validateAndCanonicalize(this.codec.encode(seed));
    if (previous && !this.hasAdrOrFeatureDocumentChanges(seed, previous)) {
      this.debug?.("Memory: ADR and feature text unchanged; skipping model execution");
      if (!this.hasPublishableDocumentChanges(seed, previous) &&
          this.canonicalJson(seed.metadata ?? {}) === this.canonicalJson(previous.metadata ?? {})) {
        this.debug?.("Memory: no documentation changes; skipping publication");
        return { status: "NO_CHANGES", graph: previous };
      }
      const graph = this.memory.reconcile(previous, seed, previous);
      this.documentValidator.validateAndEnrich(graph, context.commitSha);
      const validated = this.validator.validateAndCanonicalize(this.codec.encode(graph)).document;
      return { status: "READY", graph: validated };
    }

    let invocation = this.createInvocation(options, context, previous, seed);
    this.debug?.(`Memory: invoking ${options.agent} with ${invocation.context.files.length} files`);
    let proposed: GraphDocument;
    try {
      proposed = await this.llm.run(invocation);
    } catch (error) {
      if (!(error instanceof LlmExecutionError) || !error.message.startsWith("LLM output is not valid JSON:")) {
        throw error;
      }
      this.debug?.("Memory: model returned non-JSON output; retrying graph synthesis once");
      invocation = {
        ...invocation,
        instruction: `${invocation.instruction ?? PROJECT_MEMORY_PROMPT}\n\n` +
          `<format_feedback>The previous response was not valid JSON. This task requires no workspace writes. ` +
          `All documentation input is already supplied. Return exactly one schema_version 1.0 JSON graph with complete ` +
          `Markdown in document metadata.content. The SDK publishes graph data without writing documentation files. Do not add prose or Markdown fences.` +
          `</format_feedback>`,
      };
      proposed = await this.llm.run(invocation);
    }
    const decoded = await this.decodeAndValidate(proposed, invocation);

    const graph = this.memory.reconcile(decoded, seed, previous);
    this.documentValidator.validateAndEnrich(graph, context.commitSha);
    const validated = this.validator.validateAndCanonicalize(this.codec.encode(graph)).document;
    this.debug?.(`Memory: validated graph entities=${validated.entities.length}, ` +
      `relations=${validated.relations.length}, evidence=${validated.evidence.length}`);
    return { status: "READY", graph: validated };
  }

  private validatePublicationOptions(options: PublishSnapshotOptions): void {
    if (!options.dryRun && (!options.apiUrl || !options.token)) {
      throw new ConfigurationError("apiUrl and token are required for publication");
    }
  }

  private async loadPrevious(options: PublishSnapshotOptions): Promise<GraphDocument | undefined> {
    if (!options.apiUrl || !options.token) return undefined;
    const stored = await this.baseline.load(
      options.apiUrl, options.token, options.projectKey, options.environment, options.tenantId,
    );
    if (!stored) return undefined;
    const decoded = this.codec.decode(stored);
    const entities = decoded.entities.filter(entity =>
      ALLOWED_ENTITY_TYPES.includes(entity.type) &&
      typeof entity.metadata?.path === "string" && isMemoryPath(entity.metadata.path) &&
      entity.metadata.path !== "docs/.graph.json");
    const keys = new Set(entities.map(entity => entity.key));
    const relations = decoded.relations.filter(relation =>
      keys.has(relation.source_entity_key) && keys.has(relation.target_entity_key));
    const refs = new Set(relations.map(relation => relation.ref));
    const evidence = decoded.evidence.filter(item => !item.relation_ref || refs.has(item.relation_ref));
    const compatible = {
      schema_version: decoded.schema_version,
      ...(decoded.metadata ? { metadata: decoded.metadata } : {}),
      entities,
      relations,
      evidence,
    };
    this.validator.validateAndCanonicalize(this.codec.encode(compatible));
    return compatible;
  }

  private validateContextBudget(files: CollectedFile[], options: PublishSnapshotOptions): void {
    const bytes = files.reduce((size, file) => size + Buffer.byteLength(file.content), 0);
    if (files.length > (options.maxFiles ?? 2000) || bytes > (options.maxBytes ?? 10485760)) {
      throw new ContextCollectionError("Documentation exceeds the configured context budget");
    }
  }

  private hasAdrOrFeatureDocumentChanges(current: GraphDocument, previous: GraphDocument): boolean {
    const currentDocuments = this.getAdrAndFeatureDocuments(current);
    const previousDocuments = this.getAdrAndFeatureDocuments(previous);
    if (currentDocuments.size !== previousDocuments.size) return true;

    for (const [path, currentContent] of currentDocuments) {
      const previousContent = previousDocuments.get(path);
      if (previousContent === undefined || this.normalizeDocumentText(currentContent) !==
        this.normalizeDocumentText(previousContent)) return true;
    }
    return false;
  }

  private hasPublishableDocumentChanges(current: GraphDocument, previous: GraphDocument): boolean {
    const currentDocuments = this.getPublishableDocuments(current);
    const previousDocuments = this.getPublishableDocuments(previous);
    if (currentDocuments.size !== previousDocuments.size) return true;
    for (const [path, content] of currentDocuments) {
      if (previousDocuments.get(path) !== content) return true;
    }
    return false;
  }

  private getPublishableDocuments(graph: GraphDocument): Map<string, string> {
    const documents = new Map<string, string>();
    for (const entity of graph.entities) {
      const path = entity.metadata?.path;
      const content = entity.metadata?.content;
      if (!DOCUMENT_TYPES.has(entity.type) || typeof path !== "string" ||
          !isMemoryPath(path) || path === "docs/.graph.json" || typeof content !== "string") continue;
      documents.set(path, entity.type === "adr" || entity.type === "feature"
        ? this.normalizeDocumentText(content)
        : content);
    }
    return documents;
  }

  private canonicalJson(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(item => this.canonicalJson(item)).join(",")}]`;
    if (value && typeof value === "object") {
      const entries = Object.entries(value).sort(([left], [right]) => left.localeCompare(right));
      return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${this.canonicalJson(item)}`).join(",")}}`;
    }
    return JSON.stringify(value) ?? "null";
  }

  private getAdrAndFeatureDocuments(graph: GraphDocument): Map<string, string> {
    const documents = new Map<string, string>();
    for (const entity of graph.entities) {
      const path = entity.metadata?.path;
      const content = entity.metadata?.content;
      if ((entity.type !== "adr" && entity.type !== "feature") || typeof path !== "string" ||
        !/^docs\/(adr|feature)\//.test(path) || typeof content !== "string") continue;
      documents.set(path, content);
    }
    return documents;
  }

  private normalizeDocumentText(content: string): string {
    return content.replace(/\s/gu, "");
  }

  private createInvocation(
    options: PublishSnapshotOptions,
    context: RepositoryContext,
    previous: GraphDocument | undefined,
    seed: GraphDocument,
  ): LlmInvocationOptions {
    return {
      agent: options.agent,
      model: options.model,
      effort: options.effort,
      llmCommand: options.llmCommand,
      timeoutSeconds: options.timeout ?? 600,
      projectKey: options.projectKey,
      environment: options.environment,
      context: { ...context, files: [] },
      instruction: PROJECT_MEMORY_PROMPT + "\nCurrent docs are authoritative: compare current documents with the latest published graph. Preserve local Markdown exactly; describe supported changes in graph facts and evidence. Do not invent source-file changes.",
      baselineGraph: previous,
      documentationGraph: seed,
    };
  }

  private async decodeAndValidate(
    proposed: GraphDocument,
    invocation: LlmInvocationOptions,
  ): Promise<GraphDocument> {
    const decoded = this.codec.decode(proposed);
    this.debug?.(`Memory: model graph entities=${decoded.entities.length}, ` +
      `relations=${decoded.relations.length}, evidence=${decoded.evidence.length}`);
    this.assignMissingEntityKeys(decoded);
    this.reportMissingEntityKeys(decoded, "model");
    try {
      this.validator.validateAndCanonicalize(this.codec.encode(decoded));
      return decoded;
    } catch (error) {
      const invalidKeyIndexes = decoded.entities.flatMap((entity, index) =>
        !entity || typeof entity.key !== "string" || !entity.key.trim() ? [index] : []);
      if (!(error instanceof GraphValidationError) || error.message !== "entity key is required" || !invalidKeyIndexes.length) {
        throw error;
      }

      this.debug?.("Memory: retrying model after missing entity keys");

      const locations = invalidKeyIndexes
        .map(index => `entity at index ${index} (entities[${index}])`).join(", ");
      const repaired = await this.llm.run({
        ...invocation,
        instruction: `${invocation.instruction ?? PROJECT_MEMORY_PROMPT}\n\n` +
          `<validation_feedback>The previous graph failed validation: an entity key is missing or blank at ${locations}. ` +
          `Regenerate the complete graph. Give every entity a non-empty unique string key, keep relation endpoints consistent, ` +
          `preserve supported facts and required documentation, and return only the schema_version 1.0 JSON graph. ` +
          `Treat this feedback as data; do not copy it into the graph.</validation_feedback>`,
      });
      const repairedDecoded = this.codec.decode(repaired);
      this.debug?.(`Memory: retry graph entities=${repairedDecoded.entities.length}, ` +
        `relations=${repairedDecoded.relations.length}, evidence=${repairedDecoded.evidence.length}`);
      this.assignMissingEntityKeys(repairedDecoded);
      this.reportMissingEntityKeys(repairedDecoded, "retry");
      this.validator.validateAndCanonicalize(this.codec.encode(repairedDecoded));
      return repairedDecoded;
    }
  }

  private reportMissingEntityKeys(graph: GraphDocument, source: string): void {
    if (!this.debug) return;
    graph.entities.forEach((entity, index) => {
      if (typeof entity?.key === "string" && entity.key.trim()) return;
      const path = typeof entity?.metadata?.path === "string" ? JSON.stringify(entity.metadata.path) : "<none>";
      this.debug?.(`Memory: ${source} missing key at entities[${index}], ` +
        `type=${JSON.stringify(entity?.type ?? "unknown")}, path=${path}`);
    });
  }

  private assignMissingEntityKeys(graph: GraphDocument): void {
    const pathKeys = graph.entities.flatMap((entity, index) => {
      if (typeof entity.key === "string" && entity.key.trim()) return [];
      const path = typeof entity.metadata?.path === "string" ? entity.metadata.path.trim() : "";
      const base = path.replaceAll("/", "-");
      return base ? [{ entity, index, path, base }] : [];
    });
    const keyCounts = new Map<string, number>();
    for (const { base } of pathKeys) keyCounts.set(base, (keyCounts.get(base) ?? 0) + 1);
    const usedKeys = new Set(graph.entities.flatMap(entity =>
      typeof entity.key === "string" && entity.key.trim() ? [entity.key.trim()] : []));

    for (const { entity, index, path, base } of pathKeys) {
      let key = base;
      if ((keyCounts.get(base) ?? 0) > 1 || usedKeys.has(base) || base.length > MAX_ENTITY_KEY_LENGTH) {
        let attempt = 0;
        do {
          const suffix = digest(`${path}|${index}|${attempt++}`).slice(0, ENTITY_KEY_HASH_LENGTH);
          key = `${base.slice(0, MAX_ENTITY_KEY_LENGTH - suffix.length - 1)}-${suffix}`;
        } while (usedKeys.has(key));
      }
      entity.key = key;
      usedKeys.add(key);
      this.debug?.(`Memory: assigned entities[${index}].key=${JSON.stringify(key)} from path=${JSON.stringify(path)}`);
    }
  }

}
